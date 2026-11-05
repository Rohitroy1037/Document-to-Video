"use client";

import { Document, Page, pdfjs } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc =
  `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type PdfViewerProps = {
  file: File | null;
  pageNumber: number;
  width: number;
  onLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onLoadError: (error: Error) => void;
};

export default function PdfViewer({
  file,
  pageNumber,
  width,
  onLoadSuccess,
  onLoadError,
}: PdfViewerProps) {
  if (!file) {
    return (
      <p className="p-8 text-center text-sm text-gray-400">
        Select a PDF to preview it.
      </p>
    );
  }

  return (
    <Document
      file={file}
      onLoadSuccess={onLoadSuccess}
      onLoadError={onLoadError}
      loading={
        <p className="p-8 text-center text-sm text-gray-400">
          Loading PDF...
        </p>
      }
      error={
        <p className="p-8 text-center text-sm text-red-300">
          Could not load the PDF.
        </p>
      }
    >
      <div className="flex justify-center">
        <Page
          pageNumber={pageNumber}
          width={width}
          renderTextLayer
          renderAnnotationLayer
        />
      </div>
    </Document>
  );
}