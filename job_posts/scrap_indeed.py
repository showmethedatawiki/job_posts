#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NAME: 
Indeed Data Scrapper

AUTHOR: 
showmethedata.wiki

DESCRIPTION: 
Scrap Indeed data in regular interval and store in structured format

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


# create and configure logger
LOG_FORMAT= "%(levelname)s %(asctime)s   - %(message)s"
logging.basicConfig(filename='logging_scrap_indeed.log', level=logging.DEBUG, format= LOG_FORMAT, filemode='w')
logger= logging.getLogger()



class ScrapIndeed:

    COUNTRY_ISO_MAP= dict(zip(["united-arab-emirate", "qatar", "saudi-arabia"], ["ae", "qa", "sa"]))
    HEADERS= {"UserAgent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'}
    SLEEP= 5 # delay between requests by page

    def __init__(self, job_title: str, location: str, debug: bool = True) -> None:
        """Scrap jobs from Indeed website.

        Args:
            job_title (str): Search term
            location (str): Country of interest. Can be either [`united-arab-emirate`, `qatar`, `saudi-arabia`] for now, however it could be extended in future with API calls to ISO country codes.
            debug (bool, optional): [Enable logging to a log file for quick debugging access]. Defaults to True.
        """
        assert isinstance(job_title, str)
        assert isinstance(location, str) and location in self.COUNTRY_ISO_MAP 
        assert isinstance(debug, bool)
     
        self.job_title= job_title
        self.location= location
        self.debug= debug
        
        self._session= requests.Session()
    
    def __repr__(self) -> str:
        return f"{ScrapIndeed}"
        
    def get_data(self, save: bool = False) -> DataFrame:
        """Get All job posts as Dataframe."""
        pages, jobs, hrefs, urls_base, urls_jobs= list(), list(), list(), list(), list()

        # pages count with pagination 
        pagination= 0

        while True:

            url= self.__get_base_url(pagination)

            logger.debug(f'Retrieving data of pagination => {pagination}')
            time.sleep(self.SLEEP)
            soup= self.__extract(url)

            # stop if contents of the second page same as previous one based on list of job ids #
            if len(pages) != 0:
                latest_job_ids= list()
                for job in soup.find_all('a', id=True):
                    if job.get('id'):
                        if job.get('id').startswith('job_'):
                            latest_job_ids.append(job.get('id'))
                
                previous_job_ids= [job.get('id') for job in pages[-1].find_all('a', id=True) if job.get('id').startswith('job_')]
                cont_iter= all(job in previous_job_ids for job in latest_job_ids )
                if cont_iter:
                    logger.debug(f'Stopped looping before pagination: {pagination}')
                    break
            
            pages.append(soup)
            urls_base.append(url)
            pagination += 10
        logger.info(f'Total pages pulled: {len(pages)}')

        for i, page in enumerate(pages):
            masks= list()
            for element in page.find('div', {'id': 'mosaic-provider-jobcards'}).find_all('a'):
                if element.get('href'):
                    mask= element.get('href').startswith('/rc')
                    if mask:
                        hrefs.append(element.get('href').split('?')[1])
                        masks.append(mask)
            logger.info(f'Total jobs for page {i+1} => {len(masks)}')

        for href in hrefs:
            url_job= self.__get_job_post_url(href)
            logger.debug(f'Job Post URL => {url_job}')
            urls_jobs.append(url_job)

        for url_job in urls_jobs:
            jobs.append(self.__extract(url_job))
        logger.info(f'Total jobs pulled => {len(jobs)}')

        output_ls= self.__transform(jobs, links=urls_jobs)

        return self.__load(output_ls, save=save)

    def __get_base_url(self, page: str = '0') -> str:
        
        if len(self.job_title.split()) > 1: #indeed specific for dealing with white space in job title
            self.job_title= self.job_title.split()[0] + "%20" + self.job_title.split()[1]

        return f"https://{self.COUNTRY_ISO_MAP[self.location]}.indeed.com/jobs?q={self.job_title}&start={page}&l"
    
    def __get_job_post_url(self, param: str) -> str:

        return f"https://{self.COUNTRY_ISO_MAP[self.location]}.indeed.com/viewjob?{param}"

    @functools.lru_cache
    def __extract(self, url: str) -> BeautifulSoup:
        
        try:
            response= self._session.get(url, headers=self.HEADERS)

        except Exception as e:
            logger.error(e)
        
        else:

            if response.status_code != 200:
                logger.error(response.status_code)
                    
            try:
                soup= BeautifulSoup(response.content, 'html.parser')
                logger.info(f'Soup created for url => {url}')

            except (SyntaxError, ImportError) as e:
                logger.error(e)

            else:
                return soup
    
    def __transform(self, data: List[BeautifulSoup], /, *, links: List[str]) -> List[NamedTuple]:
        
        Parsed= namedtuple('Parsed', 'title company_name description post_date link')
        jobs_parsed= list()

        for i, job in enumerate(data):

            try:
                p= Parsed(title= job.h1.text, company_name= list(job.find('div', {'class': 'jobsearch-JobMetadataFooter'}).children)[0].text, 
                description= job.find('div', id='jobDescriptionText').get_text().strip(), 
                post_date= list(job.find('div', {'class': 'jobsearch-JobMetadataFooter'}).children)[1].text, 
                link= links[i])
            except:
                logger.error(f'Failed to transform and bypassed for job: {i+1}')
            else:
                jobs_parsed.append(p)
                logger.info(f'Transformation successfully done for job => {i+1}')
        
        return jobs_parsed

    def __load(self, data: List[NamedTuple], /, *, save: bool = True) -> DataFrame:

        try:
            data= DataFrame.from_records(data, columns=data[0]._fields)
        except:
            logger.error('Failed to load into dataframe')
        else:
            timestamp= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if save:
                name= f"scrap_indeed_{timestamp}"
                data.to_csv(f'{name}.csv', header=True)
                logger.info(f'Saved final result as csv with name => {name}')
            return data


############### Command Line Invocation ##################################
def main():
    
    parser= argparse.ArgumentParser(description='Indeed jobs scrapper')

    parser.add_argument('--job_title', type=str, required=True, help='Job Title to Search')
    parser.add_argument('--location', type= str, required=True, help='Location. Either: ["united-arab-emirate", "qatar", "saudi-arabia"]')
    parser.add_argument('--pages', type= int, default=5, help='Amount of pages to scrap')

    args= parser.parse_args()

    scrap= ScrapIndeed(args.job_title, args.location)
    ScrapIndeed.PAGES= args.pages

    return scrap.get_data(save= True)


if __name__ == '__main__':
    tic= datetime.now()
    print(f"Started script at: {tic.strftime('%Y-%m-%d %H:%M:%S')}")

    results= main()

    toc= datetime.now()
    print(f"Done at: {toc.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"Elapsed time in seconds: {(toc-tic).total_seconds()}")
