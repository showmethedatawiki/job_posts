.. role:: raw-html-m2r(raw)
   :format: html


job_posts
=========

**Summary**
---------------

----

Scrapper for middle east jobs market.

**WHY**
-----------

----

..

   Better understand the job market in the GCC region in order to prepare well in advance for relocation.


**WHAT**
------------

----

&#x2611; Job posts from emirates, saudi-arabia and qatar regions pulled and stored raw as csv\ :raw-html-m2r:`<br>`
&#x2611; Regular and automatic trigger of data scrap by monthly (end of each month)

**HOW**
-----------

----

**Tools**
^^^^^^^^^^^^^


* Beautifulsoup
* Requests 
* Airflow
* Docker
* Docker-compose
* VScode IDE

**Techniques**
^^^^^^^^^^^^^^^^^^


* Data scrapping using Python
* Exploratory analysis
* Text mining and NLP analysis

**Next Increments**
-----------------------

----

**Code**
^^^^^^^^^^^^

TODO- Document it and generate READTHEDOCS sphinx htmls
=======================================================

TODO - Package it into a container with airflow
===============================================

TODO - Publish to dockerhub, readthedocs and github.blog
========================================================


* Abstract configs into yaml or json files
* Standarized abstract class for interacting with different modules for each job portal website
* Store data into the cloud in s3 bucket
* Setup CI/CD lifecycle 
* Write integration and unittests 
* Move execution as script via main in seperate file

**Analysis**
^^^^^^^^^^^^^^^^


* Publish HowTo guide in Jupyter-notebook
* Drive insights from the data by exploring the following:
* Enrich the data by exploiting temporal dimension 
