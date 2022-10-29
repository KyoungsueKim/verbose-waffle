# verbose-waffle (서버 컨테이너)
캠퍼스 프린터기를 사용할 때 드라이버가 윈도우밖에 없어서 아이패드를 주로 쓰는 사람들은 꼭 윈도우 노트북을 켜야 하더라구요. 그게 너무 불편해서 하나 만들었습니다. 짜잔.

![image](https://user-images.githubusercontent.com/61102713/198852430-17e54f35-a841-4abb-b39f-97ae98f1d873.png)

* 이건 클라이언트 앱이 정상적으로 작동하기 위해 필요한 도커 컨테이너형 서버입니다. 
* 클라이언트 앱으로부터 pdf 파일을 https로 받아 드라이버를 이용해 프린터 기계어(assembly)로 변환하고 이를 캠퍼스 프린터 서버로 보냅니다. (CUPS)
* 클라이언트 소스코드는 https://github.com/KyoungsueKim/super-parakeet 입니다. 
* Dockerfile을 이용해 컨테이너를 빌드해야 사용할 수 있습니다. 도커에 대한 사전 지식이 필요합니다. 
* 실제 서버는 Microsoft의 Azure에서 돌아가고 있으며 깃허브에 서버 코드 push시 자동으로 컨테이너가 빌드되어 Azure 서버에 배포되는 자동화가 적용되어있습니다. 자세한건 ./github/workflows 내부에 들어있는 CI/CD 명령 파일들을 참고하세요. 

![image](https://user-images.githubusercontent.com/61102713/198852909-05a20ce6-ae55-4b5b-8b91-0d46f9917fb4.png)
<img width="976" alt="image" src="https://user-images.githubusercontent.com/61102713/198852863-2352fd2f-10ba-431f-a570-adbff70aa2da.png">
* 캠퍼스 친구들이 이 서비스를 쓰긴 쓰는데 앱 광고를 잘 안눌러줘서 적자입니다 ㅜㅜ 광고가 많이 눌러지길 간절히 바래봅니다 .. 

## Installation
* 먼저 해당 프로젝트를 clone 해야 합니다.
```
git clone https://github.com/KyoungsueKim/verbose-waffle
cd verbose-waffle
```
* 그 다음 도커 파일을 빌드합니다. 
```
docker build --tag verbose-waffle .
```
* 빌드된 도커 이미지를 다음 명령어로 확인해보세요.
```
docker image ls
```
* 만들어진 도커 이미지를 바탕으로 컨테이너를 실행해볼까요?
```
docker run -it -p 64550:64550 verbose-waffle /bin/bash
```

## Usage
iOS 클라이언트 앱(https://github.com/KyoungsueKim/super-parakeet)에서 보내는 pdf 파일을 받아 이를 프린터 기계어(assembly)로 변환하고 캠퍼스 프린터 서버로 보내는 역할을 해줍니다. 해당 서버 컨테이너를 켜둔 체 클라이언트 소스의 'super-parakeet/Service/Requests.swift' 파일 내의 url 상수를 해당 서버의 주소로 수정하세요. 

<img width="929" alt="image" src="https://user-images.githubusercontent.com/61102713/198853336-f24d6409-1c9d-408d-8f6f-bdc56cfa9032.png">


