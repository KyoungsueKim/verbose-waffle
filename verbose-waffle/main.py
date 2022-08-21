import uvicorn
import hashlib as hash
import PyPDF2
from core.printers import *
from fastapi import FastAPI, File, UploadFile, Form

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello There!"}

@app.post("/upload_file/")
def receive_file(phone_number: str = Form(...), file: UploadFile = File(...)):
    # Create unique uuid of file
    uuid_base = hash.sha1(str(time.time()).encode('utf-8')).hexdigest()
    uuid = f"{uuid_base[0:8]}-{uuid_base[9:13]}-{uuid_base[14:18]}-{uuid_base[19:23]}-{uuid_base[24:36]}".upper()

    # Save file with name as uuid
    with open(f"temp/{uuid}.pdf", "wb+") as file_obj:
        file_obj.write(file.file.read())

    # Send pdf file to printer
    data_result = send_print_data(uuid)
    register_result = send_register_doc(uuid, file.filename, phone_number, get_page_cnt(uuid))

    print(data_result, register_result)
    return {"phone_number": phone_number, "file_name": file.filename}

if __name__ == '__main__':
    os.system('service cups start')
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)