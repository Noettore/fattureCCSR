# fattureSanRossore Downloader

[![MIT License](https://img.shields.io/badge/license-MIT-blue)](../LICENSE.md) [![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Noettore/fattureSanRossore)](#) [![GitHub go.mod Go version](https://img.shields.io/github/go-mod/go-version/Noettore/fattureSanRossore?filename=fattureDownloader%2Fgo.mod)](#) [![GitHub last commit](https://img.shields.io/github/last-commit/Noettore/fattureSanRossore)](https://github.com/Noettore/fattureSanRossore/commit/master)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- [Go](https://golang.org/) v1.14 or greater
- [LibreOffice](https://www.libreoffice.org)

### Installing

To download and install follow this steps:

1. Clone this repo (or download it):

   `$ git clone https://github.com/Noettore/fattureSanRossore`

2. Download dependencies, build and install:

   ```
   $ cd path/to/fattureSanRossore/fattureDownloader
   $ go install
   ```

### Run

To run you can simply execute the built binary.

Follow the instruction in the [manual](manual/Manuale.md) (only in italian)

## Dependencies

- [github.com/extrame/xls](https://github.com/extrame/xls)
- [github.com/pdfcpu/pdfcpu](https://github.com/pdfcpu/pdfcpu/pkg/api)
- [github.com/sqweek/dialog](https://github.com/sqweek/dialog)
- [mvdan.cc/xurls](https://mvdan.cc/xurls/v2)

## Author

- [**Ettore Dreucci**](https://ettore.dreucci.it)

## License

This project is licensed under the MIT License - see the [LICENSE.md](../LICENSE.md) file for details