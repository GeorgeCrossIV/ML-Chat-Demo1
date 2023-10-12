import os
import wget
from flask import Flask, render_template, request, jsonify, send_file
from decouple import config
from cassandra.cluster import (
    Cluster,
)
from cassandra.auth import PlainTextAuthProvider
from langchain.indexes import VectorstoreIndexCreator
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.docstore.document import Document
from langchain.document_loaders import TextLoader
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.vectorstores.cassandra import Cassandra
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings
app = Flask(__name__)

astraBundleFileTitle="secure-connect-cassio-db.zip"
ASTRA_DB_SECURE_BUNDLE_PATH = os.path.join(os.getcwd(), astraBundleFileTitle)
ASTRA_DB_TOKEN_BASED_USERNAME = 'token'
ASTRA_DB_TOKEN_BASED_PASSWORD = config('ASTRA_DB_TOKEN_BASED_PASSWORD')
ASTRA_DB_KEYSPACE = config('ASTRA_DB_KEYSPACE')
OPEN_API_KEY = config('OPEN_API_KEY')
llmProvider = 'OpenAI'
os.environ['OPENAI_API_KEY']=OPEN_API_KEY

def get_answer(question):
    # get the law PDF file
    filename = get_file()
    
    # load the PDF
    from langchain.document_loaders import PyPDFLoader
    loader = PyPDFLoader(filename)
    pages = loader.load_and_split()
    
    cqlMode = 'astra_db'
    session = getCQLSession(mode=cqlMode)
    keyspace = getCQLKeyspace(mode=cqlMode)
    
    llm = OpenAI(temperature=0)
    myEmbedding = OpenAIEmbeddings()
    
    table_name = 'vs_law_pdf_' + llmProvider

    index_creator = VectorstoreIndexCreator(
        vectorstore_cls=Cassandra,
        embedding=myEmbedding,
        text_splitter=CharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=0,
        ),
        vectorstore_kwargs={
            'session': session,
            'keyspace': keyspace,
            'table_name': table_name,
        },
    )

    myCassandraVStore = Cassandra(
        embedding=myEmbedding,
        session=session,
        keyspace=keyspace,
        table_name=table_name,
    )

    myCassandraVStore.clear()
    
    mySplitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=120)
    
    if (config('PROCESS_PDF')):
        for page in pages:
            page_chunks = mySplitter.transform_documents([page])
            myCassandraVStore.add_documents(page_chunks)
  
    index = VectorStoreIndexWrapper(vectorstore=myCassandraVStore)
      
    # Simple logic to generate an answer.
    # Replace with a chatbot model for a real application.
    if "your name" in question.lower():
        return "Hello, I'm ChatGPT!"
    else:
        answer=index.query(question, llm=llm)
        #print(answer)
        return answer
 
def get_file():
    url = "https://github.com/GeorgeCrossIV/CassIO---PDF-Law-case-questions/raw/main/McCall-v-Microsoft.pdf"
    filename = "McCall-v-Microsoft.pdf"
    
    # Check if the file exists in the current working directory
    if not os.path.exists(filename):
        filename = wget.download(url)  # Only download if file doesn't exist
    
    return filename
       
def getCQLSession(mode='astra_db'):
    if mode == 'astra_db':
        cluster = Cluster(
            cloud={
                "secure_connect_bundle": ASTRA_DB_SECURE_BUNDLE_PATH,
            },
            auth_provider=PlainTextAuthProvider(
                ASTRA_DB_TOKEN_BASED_USERNAME,
                ASTRA_DB_TOKEN_BASED_PASSWORD,
            ),
        )
        astraSession = cluster.connect()
        return astraSession
    else:
        raise ValueError('Unsupported CQL Session mode')

def getCQLKeyspace(mode='astra_db'):
    if mode == 'astra_db':
        return ASTRA_DB_KEYSPACE
    else:
        raise ValueError('Unsupported CQL Session mode')
    

@app.route('/', methods=['GET', 'POST'])
def index():
    answer = ''
    if request.method == 'POST':
        question = request.form['question']
        answer = get_answer(question)
    return render_template('index.html', answer=answer)

@app.route('/ask', methods=['POST'])
def ask():
    question = request.get_json().get('question', '')
    answer = get_answer(question)
    return jsonify(answer=answer)

if __name__ == '__main__':
    app.run(debug=True)
