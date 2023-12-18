import os, subprocess
import time
import PyPDF2
import requests
import random


def get_page_cnt(id: str) -> int:
    with open(f'temp/{id}.pdf', 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        cnt = len(pdf_reader.pages)

    return cnt


def __print_to_file(id: str):
    # Create Virtual Printer
    subprocess.check_call(f'lpadmin -p {id} -v file:///root/{id}.prn -E -m CNRCUPSIRADV45453ZK.ppd'.split(' '))

    # Print pdf file via the virtual printer
    subprocess.check_call(f'lpr -P {id} -o ColorModel=KGray temp/{id}.pdf'.split(' '))

    # Wait until the job is done
    while (True):
        if "idle".encode('utf-8') in subprocess.check_output(f'lpstat -p {id}'.split(' '), timeout=180):
            break
        time.sleep(1)

    # Delete printer after fileDevice print.
    subprocess.check_call(f'lpadmin -x {id}'.split(' '))

    return f"/root/{id}.prn" if os.path.isfile(f"/root/{id}.prn") else None


def send_print_data(id: str):
    if __print_to_file(id) is not None:
        file_name = f"{id}.prn"
        server = 'http://218.145.52.6:8080/spbs/upload_bin'
        header = {'Content-Type': 'application/X-binary; charset=utf-8',
                  'User-Agent': None,
                  'Content-Disposition': f"attachment; filename={file_name}",
                  'Expect': "100-continue"}
        data = open(f'/root/{file_name}', 'rb')
        response = requests.post(url=server,
                                 headers=header,
                                 data=data)

        return response

    else:
        return None


def send_register_doc(id: str, doc_name: str, phone_number: str, cnt: int, isA3: bool = False):
    file_name = f"{id}.prn"
    server = 'http://u-printon.canon-bs.co.kr:62301/nologin/regist_doc/'
    header = {'Content-Type': 'application/json; charset=utf-8',
              'User-Agent': None,
              'Content-Disposition': f"attachment; filename={file_name}",
              'Expect': "100-continue"}
    json = {
        "nonmember_id": f"{phone_number}",
        "franchise": 28,
        "pc_mac": f"{id[-12:]}",
        "docs": [
            {
                "doc_name": f"{doc_name}",
                "queue_id": f"{id}",
                "pc_ip": f"192.168.{str(random.randrange(0, 25, 1))}.{str(random.randrange(0, 255, 1))}",
                "pages": [
                    {
                        "size": "A4",
                        "color": 0,
                        "cnt": cnt
                    }
                ]
            }
        ]
    }
    response = requests.post(url=server,
                             headers=header,
                             json=json)

    return response


def delete_print_data(id: str):
    file_name = f"{id}.prn"

    # delete pdf and prn file after send print data
    if os.path.exists(f'/root/{file_name}') and os.path.exists(f'temp/{id}.pdf'):
        os.remove(f'/root/{file_name}')
        os.remove(f'temp/{id}.pdf')

    return