import uvicorn
import hashlib as hash
from core.printers import *
from core import html_content
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/")
async def root():
    return HTMLResponse(content=html_content.html_content, status_code=200)


@app.post("/upload_file/")
async def receive_file(phone_number: str = Form(...), file: UploadFile = File(...)):
    # Create unique uuid of file
    uuid_base = hash.sha1(str(time.time()).encode('utf-8')).hexdigest()
    uuid = f"{uuid_base[0:8]}-{uuid_base[9:13]}-{uuid_base[14:18]}-{uuid_base[19:23]}-{uuid_base[24:36]}".upper()

    # Create directory if doesn't exists.
    if not os.path.exists('temp/'):
        os.makedirs('temp/')

    # Save file with name as uuid
    with open(f"temp/{uuid}.pdf", "wb+") as file_obj:
        file_obj.write(file.file.read())

    page_count = get_page_cnt(uuid)

    # Send pdf file to printer
    data_result = send_print_data(uuid)
    register_result = send_register_doc(uuid, file.filename, phone_number, page_count)
    await delete_print_data(uuid)

    print(
        f"[Print Job]: {file.filename}, page_count: {page_count}, phone_number: {phone_number}, data_result: {data_result}, register_result: {register_result}")
    return {"phone_number": phone_number, "file_name": file.filename}


if __name__ == '__main__':
    server_fullchain: str = "/etc/letsencrypt/live/kksoft.kr/fullchain1.pem"
    server_private_key: str = "/etc/letsencrypt/live/kksoft.kr/privkey1.pem"
    if not os.path.isfile(server_fullchain) or not os.path.isfile(server_private_key):
        print("SSL Certificate file does not exist. Exit the fastapi instance.")
        exit(1)

    os.system('service cups start')
    uvicorn.run("main:app", host="0.0.0.0", port=64550, reload=False, ssl_certfile=server_fullchain,
                ssl_keyfile=server_private_key)
