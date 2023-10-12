# ML-PDF-Chat
This repository contains a Flask application that will enable a user to ask questions about the contents of a PDF. The code downloads a PDF that's a legal case for Microsoft vs McCall. The application will attempt to connect to an Astra DB database that contains embeddings of the PDF. 

If the .env variable [RPCESS_PDF is true, the PDF will refresh the embeddings of the PDF.
