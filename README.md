# fattureCCSR

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](LICENSE.md) [![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Noettore/fattureSanRossore)](#) [![GitHub last commit](https://img.shields.io/github/last-commit/Noettore/fattureSanRossore)](https://github.com/Noettore/fattureSanRossore/commit/master)

## The Project
This utility has the only purpose of facilitate the tasks of downloading invoices and generating TeamSystem's TRAF2000 record from a CCSR report.    
It allows the user to authenticate to the CCSR SQL Server Reporting Services (SSRS) and after specifying a time interval it download the suitable report and lets generate the TRAF2000 record or download and merge all the invoices issued in that period.

## How to run
Simply by cloning the repo, installing the required packages and executing the main script file:
```
$ git clone https://github.com/Noettore/fattureCCSR.git
$ cd fattureCCSR
$ pip install -r ./requirements.txt
$ python ./fatture_ccsr/fatture_ccsr.py
```

## How to generate a one-file distributable
Using [pyinstaller](https://www.pyinstaller.org/):
```
$ pip install -U pyinstaller
$ cd fattureCCSR/fatture_ccsr
$ pyinstaller -clean ./fatture_ccsr.spec
```

## Author
- [**Ettore Dreucci**](https://ettore.dreucci.it)

## License
This project is licensed under the MIT License - see the [LICENSE.md](/LICENSE.md) file for details
