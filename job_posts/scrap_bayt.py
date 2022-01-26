#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NAME: 
Bayt Data Scrapper

AUTHOR: 
showmethedata.wiki

DESCRIPTION: 
Scrap Bayt data in regular interval and store in structured format

CONTENTS: 
The following APIs are public:
- get_data()

NOTES:
This program can be run either as a Python module (importable) or as a shell script from terminal.
"""

import requests
from bs4 import BeautifulSoup
from collections import namedtuple
from datetime import datetime
import logging
from time import time
import time
import functools
from pandas import DataFrame
from typing import List, NamedTuple
import argparse
import sys

# create and configure logger
LOG_FORMAT = "%(levelname)s %(asctime)s   - %(message)s"
logging.basicConfig(filename=f'../logs/logging_scrap_bayt.log',
                    level=logging.DEBUG, format=LOG_FORMAT, filemode='w')
logger = logging.getLogger()


class ScrapBayt:

    COUNTRY_ISO_MAP = dict(zip(
        ["united-arab-emirate", "qatar", "saudi-arabia"], ["uae", "qatar", "saudi-arabia"]))
    HEADERS = {
        'authority': 'www.bayt.com',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-US,en;q=0.9,de;q=0.8'}
    SLEEP = 10  # delay between requests by page

    def __init__(self, job_title: str, location: str) -> None:
        """Scrap jobs from Indeed website.

        Args:
            job_title (str): Search term
            location (str): Country of interest. Can be either [`united-arab-emirate`, `qatar`, `saudi-arabia`] for now, however it could be extended in future with API calls to ISO country codes.
            debug (bool, optional): [Enable logging to a log file for quick debugging access]. Defaults to True.
        """
        assert isinstance(job_title, str)
        assert isinstance(location, str) and location in self.COUNTRY_ISO_MAP

        self.job_title = job_title
        self.location = location

        self._session = requests.Session()

    def __repr__(self) -> str:
        return f"{ScrapBayt}"

    def get_data(self, save: bool = False) -> DataFrame:

        job_ids, soups = list(), list()
        page = 1

        # Get job ids from all pages #
        while True:
            url = self.__get_url(page)
            time.sleep(self.SLEEP)
            soup = self.__extract(url)
            logger.info(f'Created a soup for page: {page}')

            latest_job_ids = self.__get_jobs_id(soup)
            logger.info(f'Found {len(latest_job_ids)} jobs for page => {page}')

            if job_ids:  # stop iteration after pagination is complete.
                if job_ids[-1] == latest_job_ids:
                    break

            job_ids.append(latest_job_ids)
            page += 1
        total_jobs = sum([len(jobs) for jobs in job_ids])
        logger.info(f'Total jobs found: {total_jobs}')
        logger.info(f'Total job ids: {job_ids}')

        # Extract all jobs #

        # Exit if no joubs were found
        if not job_ids[0]:
            logging.warning(f'No matching jobs were found!')
            sys.exit(0)

        cnt = 0
        urls = list()
        for page in range(0, len(job_ids)):
            cnt += 1
            page += 1

            for job_id in job_ids[page]:

                url = f"{self.__get_url(page)}&jobId={job_id}"
                logger.info(f'Making API request for job url => {url}')
                urls.append(url)

                time.sleep(self.SLEEP)
                soups.append(self.__extract(url))
                logger.info(
                    f'Completed extraction of {cnt} out of {total_jobs} jobs')
                print(f'Extracted job {cnt} out of {total_jobs}')
                cnt += 1

        # Transform #
        data = self.__transform(soups, links=urls)
        # Load #
        return self.__load(data)

    def __get_url(self, page: int, /) -> str:

        # indeed specific for dealing with white space in job title
        if len(self.job_title.split()) > 1:
            self.job_title = self.job_title.split(
            )[0] + "-" + self.job_title.split()[1]

        return f"https://www.bayt.com/en/{self.COUNTRY_ISO_MAP[self.location]}/jobs/{self.job_title}-jobs/?page={page}"

    @functools.lru_cache
    def __extract(self, url: str) -> BeautifulSoup:
        return BeautifulSoup(self._session.get(url, headers=self.HEADERS).text, 'html.parser')

    def __get_jobs_id(self, soup: BeautifulSoup, /) -> List[int]:
        return [element.get('data-job-id') for element in soup.find('div', {'id': 'results_inner_card', 'class': 'card-content'}).find_all('li', {"data-job-id": True})]

    def __transform(self, data: List[BeautifulSoup], /, *, links: List[str]) -> List[NamedTuple]:

        Parsed = namedtuple(
            'Parsed', 'title company_name description post_date link')
        jobs_parsed = list()

        for i, job in enumerate(data):

            try:
                p = Parsed(title=job.h2.text, company_name=job.find('a', class_='is-black').text,
                           description=job.find(
                               class_="card-content t-small bt p20").text.strip(),
                           post_date='-'.join(
                               job.find('span', class_='p20l-d p10y-m u-block-m').text.strip().split()[-2:]),
                           link=links[i])
            except:
                logger.error(
                    f'Failed to transform and bypassed for job: {i+1}')
            else:
                jobs_parsed.append(p)
                logger.info(
                    f'Transformation successfully done for job => {i+1}')

        return jobs_parsed

    def __load(self, data: List[NamedTuple], /, *, save: bool = True) -> DataFrame:

        try:
            data = DataFrame.from_records(data, columns=data[0]._fields)
        except:
            logger.error('Failed to load into dataframe')
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if save:
                name = f"scrap_bayt_{timestamp}"
                data.to_csv(f'../data/{name}.csv', header=True)
                logger.info(f'Saved final result as csv with name => {name}')
            return data


############### Command Line Invocation ##################################
def main():

    parser = argparse.ArgumentParser(description='Indeed jobs scrapper')

    parser.add_argument('--job_title', type=str,
                        required=True, help='Job Title to Search')
    parser.add_argument('--location', type=str, required=True,
                        help='Location. Either: ["united-arab-emirate", "qatar", "saudi-arabia"]')
    parser.add_argument('--pages', type=int, default=5,
                        help='Amount of pages to scrap')

    args = parser.parse_args()

    scrap = ScrapBayt(args.job_title, args.location)
    ScrapBayt.PAGES = args.pages

    return scrap.get_data(save=True)


if __name__ == '__main__':
    tic = datetime.now()
    print(f"Started script at: {tic.strftime('%Y-%m-%d %H:%M:%S')}")

    results = main()

    toc = datetime.now()
    print(f"Done at: {toc.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"Elapsed time in seconds: {(toc-tic).total_seconds()}")
