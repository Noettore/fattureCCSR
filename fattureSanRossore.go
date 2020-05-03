package main

import (
	"bufio"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"

	"github.com/extrame/xls"
	"github.com/pdfcpu/pdfcpu/pkg/api"
	"github.com/sqweek/dialog"
	"mvdan.cc/xurls/v2"
)

var tmpDir string
var outDir string
var mw io.Writer
var logPath string
var exitWithError bool

func getInvoiceIDs(fileName string) []string {
	xlFile, err := xls.Open(fileName, "utf-8")
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile aprire il file xls: %v\n", err)
	}

	sheet := xlFile.GetSheet(0)
	if sheet == nil {
		exitWithError = true
		log.Panicf("Impossibile aprire il foglio nell'xls: %v\n", err)
	}

	var invoiceIDs []string

	for i := 4; i <= int(sheet.MaxRow); i++ {
		row := sheet.Row(i)
		if row.Col(8) != "" {
			id := strings.ReplaceAll(row.Col(8), "/", "-")
			invoiceIDs = append(invoiceIDs, id)
		}
	}
	return invoiceIDs
}

func convertXLStoFODS(fileName string) string {
	var sofficePath string = "libreoffice"
	if runtime.GOOS == "windows" {
		sofficePath = filepath.FromSlash("C:/Program Files/LibreOffice/program/soffice.exe")
	}
	cmd := exec.Command(sofficePath, "--convert-to", "fods", "--outdir", outDir, fileName)
	cmd.Stdout = mw
	cmd.Stderr = mw
	err := cmd.Run()
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile convertire l'XLS in FODS: %v\n", err)
	}
	return (outDir + "/" + strings.TrimSuffix(filepath.Base(fileName), filepath.Ext(fileName)) + ".fods")
}

func getInvoiceURLs(fileName string) []string {
	fods := convertXLStoFODS(fileName)
	f, err := os.Open(fods)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile aprire il FODS convertito: %v\n", err)
	}
	defer func() {
		err = f.Close()
		if err != nil {
			log.Printf("Impossibile chiudere il file %v: %v\n", fods, err)
		}
	}()
	var invoiceURLs []string
	s := bufio.NewScanner(f)
	for s.Scan() {
		line := s.Text()
		if strings.Contains(line, "http://report.casadicurasanrossore.it:9146/files/get?type=invoice&amp;id=") {
			url := xurls.Strict().FindString(line)
			url = strings.ReplaceAll(url, "&amp;", "&")
			invoiceURLs = append(invoiceURLs, url)
		}
	}
	if err := s.Err(); err != nil {
		exitWithError = true
		log.Panicf("Impossibile leggere dal file %v: %v\n", fods, err)
	}
	return invoiceURLs
}

func checkFile(fileName string) string {
	_, err := os.Stat(fileName)
	if err != nil {
		exitWithError = true
		log.Panicf("Errore nell'apertura del file %v: %v\n", fileName, err)
	}
	absPath, err := filepath.Abs(fileName)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile recuperare il percorso assoluto del file %v: %v\n", fileName, err)
	}
	return absPath
}

func downloadFile(fileName string, url string) error {
	resp, err := http.Get(url)

	if err != nil {
		resp.Body.Close()
		return err
	}

	out, err := os.Create(fileName)
	if err != nil {
		out.Close()
		return err
	}

	_, err = io.Copy(out, resp.Body)
	out.Close()
	resp.Body.Close()

	return err
}

func createTmpDir() string {
	dir := filepath.FromSlash(tmpDir + "/fattureSanRossore")

	if _, err := os.Stat(dir); err == nil {
		log.Printf("Pulizia della directory temporanea pre-esistente")
		err := os.RemoveAll(dir)
		if err != nil {
			exitWithError = true
			log.Panicf("Impossibile eliminare la directory temporanea pre-esistente %v: %v\n", dir, err)
		}
	} else if !os.IsNotExist(err) {
		exitWithError = true
		log.Panicf("Impossibile eseguire lo stat sulla directory temporanea %v: %v\n", dir, err)
	}
	err := os.Mkdir(dir, os.ModePerm)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile creare la directory temporanea di salvataggio %v: %v\n", dir, err)
	}

	return dir
}

func downloadInvoices(ids []string, urls []string) []string {
	if len(ids) != len(urls) {
		exitWithError = true
		log.Panicf("Il numero di fatture da scaricare non corrisponde al numero di URL individuati nel file")
	}

	wg := sync.WaitGroup{}
	sem := make(chan bool, 30)
	mu := sync.Mutex{}
	invoiceNum := len(ids)
	downloadCount := 0
	downloadedFiles := make([]string, invoiceNum)

	log.Printf("Inizio il download di %d fatture\n", invoiceNum)
	for i := 0; i < invoiceNum; i++ {
		id := ids[i]
		url := urls[i]
		out := filepath.FromSlash(outDir + "/" + id + ".pdf")

		wg.Add(1)
		go func(i int) {
			sem <- true
			log.Printf("Scaricamento di %v\n", id)
			err := downloadFile(out, url)
			if err != nil {
				log.Printf("Impossibile scaricare il file %v: %v\n", url, err)
			} else {
				downloadedFiles[i] = out
				mu.Lock()
				downloadCount++
				mu.Unlock()
			}
			<-sem
			wg.Done()
		}(i)
	}
	wg.Wait()
	log.Printf("Scaricate %d/%d fatture\n", downloadCount, invoiceNum)
	return downloadedFiles[:downloadCount]
}

func mergeInvoices(files []string) string {
	out, err := dialog.File().Filter("PDF files", "pdf").Title("Scegli dove salvare le fatture unite").Save()
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile recuperare il file selezionato: %v\n", err)
	}
	if filepath.Ext(out) == "" {
		out += ".pdf"
	}
	err = api.MergeFile(files, out, nil)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile unire i pdf: %v\nFatture singole non rimosse\n", err)
	}
	return out
}

func openPDF(fileName string) {
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C start "+fileName)

	} else {
		cmd = exec.Command("xdg-open", fileName)
	}
	cmd.Stdout = mw
	cmd.Stderr = mw
	err := cmd.Start()
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile aprire il pdf con le fatture unite: %v\n", err)
	}
}

func cleanTmpDir() {
	files, err := ioutil.ReadDir(outDir)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile recuperare la lista di file creati nella directory temporanea: %v\n", err)
	}
	for _, file := range files {
		err = os.Remove(filepath.FromSlash(outDir + "/" + file.Name()))
		if err != nil {
			log.Printf("Impossibile eliminare la fattura singola %v: %v\n", file, err)
		}
	}
	err = os.Remove(outDir)
	if err != nil {
		log.Printf("Impossibile eliminare la directory temporanea %v: %v\n", outDir, err)
	}
}

func main() {
	exitWithError = false
	args := os.Args
	tmpDir = os.TempDir()

	if runtime.GOOS == "linux" {
		logPath = tmpDir + "/log_fattureSanRossore.log"
	} else {
		logPath = filepath.FromSlash(tmpDir + "/log_fattureSanRossore.txt")
	}
	logFile, err := os.OpenFile(filepath.FromSlash(logPath), os.O_CREATE|os.O_TRUNC|os.O_RDWR, 0666)
	if err != nil {
		exitWithError = true
		log.Panicf("Impossibile creare il file di log: %v\n", err)
	}
	mw = io.MultiWriter(os.Stderr, logFile)
	log.SetOutput(mw)

	defer func() {
		if !exitWithError {
			cleanTmpDir()
		} else {
			log.Println("I file temporanei non sono stati eliminati per poterli riesaminare")
		}
		log.Printf("Log file salvato in %v\n", logPath)
	}()

	outDir = createTmpDir()

	var fileName string
	if len(args) < 2 {
		var err error
		fileName, err = dialog.File().Filter("XLS files", "xls").Load()
		if err != nil {
			exitWithError = true
			log.Panicf("Impossibile recuperare il file selezionato: %v\n", err)
		}
	} else {
		fileName = args[1]
	}

	filePath := checkFile(fileName)
	IDs := getInvoiceIDs(filePath)
	URLs := getInvoiceURLs(filePath)
	dlFiles := downloadInvoices(IDs, URLs)
	pdf := mergeInvoices(dlFiles)
	openPDF(pdf)
}
