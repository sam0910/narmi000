## :rocket: 펌웨어 업데이트

-   src/app 아래 파일들만 기기로 업데이트 됩니다.

-   기기전원 ON 후 즉시, 버튼 2개 누르고 있으면, 현재 깃헙 레포지토리 버젼(새로운 버젼 발견시)으로 펌웨어 업데이트 진행합니다.

    업데이트 모드 진입시,

    1. 주변 Wifi 중 와이파이 비번이 12345678( [src/app/common.py](https://github.com/sam0910/narmi000/blob/main/src/app/common.py) - INITIAL_WIFI_PASSWORD ) 연결 시도
    2. [src/app/secrets.py](https://github.com/sam0910/narmi000/blob/main/src/app/secrets.py) 내의 지정된 Wifi로 접속 시도

    ```
    WIFI_SSID = "KT_GiGA_xxxxx"
    WIFI_PASSWORD = "4bbbxxxxx"
    ```

    3. Wifi 연결 후 Github repo release version 체크 후 높은 버젼 발견시 src/app 아래 파일을 기기로 업데이트

## :rocket: 파일 설명

-   [src/boot.py](https://github.com/sam0910/narmi000/blob/main/src/boot.py) : 기기 On 시 제일 먼저 실행되는 파일입니다. 업데이트 모드 여부 판정 후 src/app/start.py 파일을 실행 합니다.

-   [src/app/start.py](https://github.com/sam0910/narmi000/blob/main/src/app/start.py) : 초기 실행 파일 입니다.

-   [src/calibration.py](https://github.com/sam0910/narmi000/blob/main/src/calibration.py) : 온습도 센서 칼리브레이션 파일 입니다.

    ### 펌웨어 관련은 [Micropython 관련문서](https://docs.micropython.org/en/latest/) 참고 부탁드립니다.

## :rocket: USB UART

> CP2102 모듈 추천 ... [구매링크](https://robotscience.kr/goods/view?no=14262&gad_source=1&gbraid=0AAAAACWB_n-m_x6At5UWQn2Q6Hc8YhFkc&gclid=CjwKCAiAmfq6BhAsEiwAX1jsZ2Iw9Hm85rxKg5IMHjzzwXI6OYQJh3hXjFVWU3ZfzOAzd248pVO96hoCz94QAvD_BwE)
