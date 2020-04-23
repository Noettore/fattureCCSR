package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/extrame/xls"
	"github.com/pdfcpu/pdfcpu/pkg/api"
	"github.com/sqweek/dialog"
	"mvdan.cc/xurls/v2"
)

var tmp string = os.TempDir()

func getInvoiceIDs(fileName string) []string {
	xlFile, err := xls.Open(fileName, "utf-8")
	if err != nil {
		log.Fatalf("Impossibile aprire il file xls: %v\n", err)
	}

	sheet := xlFile.GetSheet(0)
	if sheet == nil {
		log.Fatalf("Impossibile aprire il foglio nell'xls: %v\n", err)
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
	cmd := exec.Command(sofficePath, "--convert-to", "fods", "--outdir", tmp, fileName)
	err := cmd.Run()
	if err != nil {
		log.Fatalf("Impossibile convertire l'XLS in FODS: %v\n", err)
	}
	return (tmp + "/" + strings.TrimSuffix(filepath.Base(fileName), filepath.Ext(fileName)) + ".fods")
}

func getInvoiceURLs(fileName string) []string {
	fods := convertXLStoFODS(fileName)
	f, err := os.Open(fods)
	if err != nil {
		log.Fatalf("Impossibile aprire il FODS convertito: %v\n", err)
	}
	defer func() {
		err = f.Close()
		if err != nil {
			log.Printf("Impossibile chiudere il file %v: %v\n", fods, err)
		}
		err = os.Remove(fods)
		if err != nil {
			log.Printf("Impossibile eliminare il file temporaneo %v: %v\n", fods, err)
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
		log.Fatalf("Impossibile leggere dal file %v: %v\n", fods, err)
	}
	return invoiceURLs
}

func checkFile(fileName string) string {
	_, err := os.Stat(fileName)
	if err != nil {
		log.Fatalf("Errore nell'apertura del file %v: %v\n", fileName, err)
	}
	absPath, err := filepath.Abs(fileName)
	if err != nil {
		log.Fatalf("Impossibile recuperare il percorso assoluto del file %v: %v\n", fileName, err)
	}
	return absPath
}

func downloadFile(fileName string, url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	out, err := os.Create(fileName)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

func downloadInvoices(ids []string, urls []string) []string {
	if len(ids) != len(urls) {
		log.Fatalf("Il numero di fatture da scaricare non corrisponde al numero di URL individuati nel file")
	}

	dir := filepath.FromSlash(tmp + "/pdfInvoices" + "_" + time.Now().Format("20060102"))
	err := os.Mkdir(dir, os.ModePerm)
	if err != nil {
		log.Fatalf("Impossibile creare la directory temporanea di salvataggio %v: %v\n", dir, err)
	}

	downloadCount := 0
	var downloadedFiles []string
	for i := 0; i < len(ids); i++ {
		out := filepath.FromSlash(dir + "/" + ids[i] + ".pdf")

		fmt.Printf("Scaricamento di %v\n", ids[i])
		err = downloadFile(out, urls[i])
		if err != nil {
			log.Printf("Impossibile scaricare il file %v: %v\n", urls[i], err)
		} else {
			downloadCount++
			downloadedFiles = append(downloadedFiles, out)
		}
	}
	fmt.Printf("Scaricate %d/%d fatture\n", downloadCount, len(ids))
	return downloadedFiles
}

func mergeInvoices(files []string) string {
	out, err := dialog.File().Filter("PDF files", "pdf").Title("Scegli dove salvare le fatture unite").Save()
	if err != nil {
		log.Fatalf("Impossibile recuperare il file selezionato: %v\n", err)
	}
	if filepath.Ext(out) == "" {
		out += ".pdf"
	}
	err = api.MergeFile(files, out, nil)
	if err != nil {
		log.Fatalf("Impossibile unire i pdf: %v\nFatture singole non rimosse\n", err)
	}
	dir := filepath.Dir(files[0])
	for _, file := range files {
		err = os.Remove(file)
		if err != nil {
			log.Printf("Impossibile eliminare la fattura singola %v: %v\n", file, err)
		}
	}
	err = os.Remove(dir)
	if err != nil {
		log.Printf("Impossibile eliminare la directory temporanea %v: %v\n", dir, err)
	}
	return out
}

func openPDF(fileName string) {
	if runtime.GOOS == "windows" {
		cmd := exec.Command("cmd", "/C start "+fileName)
		err := cmd.Run()
		if err != nil {
			log.Fatalf("Impossibile aprire il pdf con le fatture unite: %v\n", err)
		}
	}
	//TODO for Linux
}

func main() {
	var fileName string

	args := os.Args
	if len(args) < 2 {
		var err error
		fileName, err = dialog.File().Filter("XLS files", "xls").Load()
		if err != nil {
			log.Fatalf("Impossibile recuperare il file selezionato: %v\n", err)
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
