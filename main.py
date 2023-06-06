import os
import tkinter as tk
from tkinter import ttk
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from PIL import Image, ImageTk
from io import BytesIO
import matplotlib.pyplot as plt
import telepot
from telepot.loop import MessageLoop

#import spam

api_key = ""
api_url = ""
map_url = ""
map_key = ""
chat_id = ''
bot_token = ""

#print(spam)
#print(spam.strlen("Spam Module Test"))

bot = telepot.Bot(bot_token)

def handle_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type == 'text':
        command = msg['text']
        if command == '/start':
            bot.sendMessage(chat_id, "안녕하세요! 응급실 찾기 프로그램입니다.")
        elif command == '/search':
            bot.sendMessage(chat_id, "검색하고 싶은 내용을 입력해주세요(이름/지역)")
            handle_search(chat_id, command)

def telegram_button_clicked(event=None):
    os.system("C:/Telegram/Telegram.exe")
    bot.message_loop(handle_message)

def handle_search(chat_id, command):
    selected_region = ""
    selected_name = ""
    # 검색어를 지역과 이름으로 분리
    keywords = command.split("/")
    if len(keywords) == 2:
        selected_region = keywords[0].strip()
        selected_name = keywords[1].strip()
    elif len(keywords) == 1:
        selected_name = keywords[0].strip()

    emergency_rooms = get_emergency_rooms_data()

    result = ""
    for room in emergency_rooms:
        address = room.findtext("dutyAddr")
        name = room.findtext("dutyName")

        if (not selected_region or address.startswith(selected_region)) and \
                (not selected_name or selected_name.lower() in name.lower()):
            phone = room.findtext("dutyTel1")
            result += f"이름: {name}\n주소: {address}\n전화번호: {phone}\n\n"

    if result:
        bot.sendMessage(chat_id, result)
    else:
        bot.sendMessage(chat_id, "검색 결과가 없습니다.")

class MapViewer:
    def __init__(self, parent):
        self.parent = parent
        self.canvas = tk.Canvas(self.parent, width=600, height=400, highlightthickness=0)
        self.canvas.place(x=350, y=120)
        self.canvas.configure(bg="#b0e0e6")
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.image = None
        self.map_image = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.load_map_image(None)
        self.current_address = ""
        self.lat = 0
        self.lng = 0
        self.start_x = 0
        self.start_y = 0
        self.zoom_level = 0
        self.marker_lat = 0
        self.marker_lng = 0

    def geocode_address(self, address):
        encoded_address = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={map_key}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "OK":
            result = data["results"][0]
            lat = result["geometry"]["location"]["lat"]  # self.lat 초기화
            lng = result["geometry"]["location"]["lng"]  # self.lng 초기화
            return lat, lng
        else:
            return None, None

    def load_map_image(self, address):
        if address is None:
            address = ""
        self.current_address = address
        lat, lng = self.geocode_address(address)
        if lat is not None and lng is not None:
            self.lat = lat
            self.lng = lng
            self.marker_lat = lat
            self.marker_lng = lng
            if self.marker_lat == 0 and self.marker_lng == 0:
                self.marker_lat = lat
                self.marker_lng = lng

            self.update_map()

    def show_map(self):
        self.canvas.delete("map_image")
        if self.map_image:
            self.image = ImageTk.PhotoImage(self.map_image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image, tags="map_image")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image, tags="map_image")
            self.canvas.configure(scrollregion=self.canvas.bbox("map_image"))

    def update_map(self):
        # 확대/축소된 지도 이미지 URL을 생성합니다.
        encoded_address = urllib.parse.quote(self.current_address)
        marker = f"{self.marker_lat},{self.marker_lng}"
        print("maker_lat =", self.marker_lat, "market_lng =", self.marker_lng)
        map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={encoded_address}&" \
                  f"zoom={14 + self.zoom_level}&size=600x400&markers=color:red%7Clabel:E%7C{marker}&key={map_key}"
        response = requests.get(map_url)
        self.map_image = Image.open(BytesIO(response.content))
        self.show_map()

    def on_mouse_press(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["item"] = self.canvas.find_closest(event.x, event.y)[0]
        self.start_x = event.x
        self.start_y = event.y

    def on_mouse_motion(self, event):
        move_x = event.x - self.start_x
        move_y = event.y - self.start_y

        self.canvas.move(self.drag_data["item"], move_x, move_y)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        # 마우스 이동에 따라 새로운 주소를 계산하여 지도를 업데이트합니다.
        map_width, map_height = self.map_image.size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        map_x = -self.canvas.coords("map_image")[0]
        map_y = -self.canvas.coords("map_image")[1]
        x_ratio = map_x / canvas_width
        y_ratio = map_y / canvas_height
        address_x = x_ratio * map_width
        address_y = y_ratio * map_height


        center_lat, center_lng = self.calculate_latlng(address_x, address_y)
        print("center_lat =", center_lat, "center_lng =", center_lng)
        print("maker_lat =", self.marker_lat, "market_lng =", self.marker_lng)
        address = f"{center_lat},{center_lng}"
        self.load_map_image(address)

    def calculate_latlng(self, address_x, address_y):
        move_x = self.start_x - self.drag_data["x"]
        move_y = self.start_y - self.drag_data["y"]
        address_x -= move_x
        address_y += move_y
        print("dx = ", move_x, "dy = ", move_y)

        self.lat += address_x * 0.00005
        self.lng += address_y * 0.00005
        return self.lat, self.lng

    def on_mouse_release(self, event):
        self.drag_data["x"] = 0
        self.drag_data["y"] = 0
        self.drag_data["item"] = None

        self.load_map_image(self.current_address)

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_level += 1
        else:
            self.zoom_level -= 1

        self.update_map()

def resize_image(image_path, width, height):
    # 이미지 로드
    image = Image.open(image_path)

    # 이미지 크기 조정
    resized_image = image.resize((width, height), Image.LANCZOS)

    # Tkinter에서 사용할 수 있는 형식으로 변환
    tk_image = ImageTk.PhotoImage(resized_image)

    return tk_image

def get_emergency_rooms_data():
    params = {
        "ServiceKey": api_key,
        "pageNo": 1,
        "numOfRows": 10000
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        emergency_rooms = root.findall(".//item")
        return emergency_rooms
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def search_emergency_rooms():
    selected_region = region_combo.get()
    selected_gugun = gugun_combo.get()
    selected_name = name_entry.get()

    emergency_rooms = get_emergency_rooms_data()

    result_text.delete(1.0, tk.END)
    if not selected_region and not selected_gugun and not selected_name:
        # 선택된 지역과 이름이 없는 경우 모든 정보를 출력
        for room in emergency_rooms:
            name = room.findtext("dutyName")
            address = room.findtext("dutyAddr")
            phone = room.findtext("dutyTel1")
            hperyn_value = room.findtext("hperyn")
            hpbdn_value = room.findtext("hpbdn")
            hpgryn_value = room.findtext("hpgryn")


            result_text.insert(tk.END, "이름: {}\n".format(name))
            result_text.insert(tk.END, "주소: {}\n".format(address))
            result_text.insert(tk.END, "전화번호: {}\n".format(phone))
            location_button = tk.Button(
                window,
                text="위치 보기",
                command=lambda addr=address: map_viewer.load_map_image(addr)
            )
            location_button.pack()
            result_text.window_create(tk.END, window=location_button)

            graph_button = tk.Button(
                window,
                text="정보보기",
                command=lambda h=hperyn_value, pc=hpbdn_value, pg=hpgryn_value: show_graph(h, pc, pg)
            )
            result_text.window_create(tk.END, window=graph_button)
            tel_button = tk.Button(
                window,
                text="전송",
                command=lambda r=room: send_emergency_rooms_to_telegram(r)
            )
            result_text.window_create(tk.END, window=tel_button)
            result_text.insert(tk.END, "\n")
            result_text.insert(tk.END, "\n----------------------\n")

    else:
        # 선택된 지역 또는 이름이 있는 경우 해당 조건에 맞는 정보를 출력
        for room in emergency_rooms:
            address = room.findtext("dutyAddr")
            name = room.findtext("dutyName")

            if (not selected_region or address.startswith(f"{selected_region}")) and \
                    (not selected_gugun or address.startswith(f"{selected_region} {selected_gugun}")) and \
                    (not selected_name or selected_name.lower() in name.lower()):
                phone = room.findtext("dutyTel1")
                hperyn_value = room.findtext("hperyn")
                hpbdn_value = room.findtext("hpbdn")
                hpgryn_value = room.findtext("hpgryn")

                result_text.insert(tk.END, "이름: {}\n".format(name))
                result_text.insert(tk.END, "주소: {}\n".format(address))
                result_text.insert(tk.END, "전화번호: {}\n".format(phone))
                location_button = tk.Button(
                    window,
                    text="위치 보기",
                    command=lambda addr=address: map_viewer.load_map_image(addr)
                )
                location_button.pack()
                result_text.window_create(tk.END, window=location_button)

                graph_button = tk.Button(
                    window,
                    text="정보보기",
                    command=lambda h=hperyn_value, pc=hpbdn_value, pg=hpgryn_value: show_graph(h, pc, pg)
                )
                result_text.window_create(tk.END, window=graph_button)
                tel_button = tk.Button(
                    window,
                    text="전송",
                    command=lambda r=room: send_emergency_rooms_to_telegram(r)
                )
                result_text.window_create(tk.END, window=tel_button)
                result_text.insert(tk.END, "\n")
                result_text.insert(tk.END, "\n----------------------\n")

def send_emergency_rooms_to_telegram(room):

    name = room.findtext("dutyName")
    address = room.findtext("dutyAddr")
    phone = room.findtext("dutyTel1")

    message = f"이름: {name}\n주소: {address}\n전화번호: {phone}"

    bot.sendMessage(chat_id, message)

def show_graph(hperyn_value, hpcuyn_value, hpgryn_value):
    # 값이 None인 경우 0으로 대체하여 타입 오류 방지
    values = [int(hperyn_value or 0), int(hpcuyn_value or 0), int(hpgryn_value or 0)]

    # 막대 그래프를 생성하여 출력
    categories = ['Emergency Rooms', 'Beds', 'inpatient room']

    plt.bar(categories, values)
    plt.xlabel('Types')
    plt.ylabel('Nums')
    plt.title('Current Situation')

    for i, value in enumerate(values):
        plt.text(i, value, str(value), ha='center', va='bottom')

    plt.show()

def show_location(address):
    global map_viewer
    map_viewer.load_map_image(address)

# search_entry를 전역 변수로 선언하여 다른 함수에서도 사용할 수 있도록 함
search_entry = None

# GUI 생성
window = tk.Tk()
map_viewer = MapViewer(window)
window.title("전국 응급실 정보")
window.geometry("1000x800")
window.configure(bg="#b0e0e6")

search_frame = tk.Frame(window)
search_frame.place(x=5, y=5)
search_frame.configure(bg="#b0e0e6")

region_label = tk.Label(search_frame, text="시/도 선택")
region_label.pack()
region_label.configure(bg="#b0e0e6")

regions = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원도",
    "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도"
]

region_combo = ttk.Combobox(search_frame, values=regions)
region_combo.pack()

gugun_label = tk.Label(search_frame, text="구/군 선택")
gugun_label.configure(bg="#b0e0e6")

gugun_dict = {
    "서울특별시": [
        "강남구", "강동구", "강북구", "강서구", "관악구",
        "광진구", "구로구", "금천구", "노원구", "도봉구",
        "동대문구", "동작구", "마포구", "서대문구", "서초구",
        "성동구", "성북구", "송파구", "양천구", "영등포구",
        "용산구", "은평구", "종로구", "중구", "중랑구"
    ],
    "부산광역시": [
        "강서구", "금정구", "기장군", "남구", "동구",
        "동래구", "부산진구", "북구", "사상구", "사하구",
        "서구", "수영구", "연제구", "영도구", "중구",
        "해운대구"
    ],
    "대구광역시": [
        "남구", "달서구", "달성군", "동구", "북구",
        "서구", "수성구", "중구"
    ],
    "인천광역시": [
        "강화군", "계양구", "남동구", "동구", "미추홀구",
        "부평구", "서구", "연수구", "옹진군", "중구"
    ],
    "광주광역시": [
        "광산구", "남구", "동구", "북구", "서구"
    ],
    "대전광역시": [
        "대덕구", "동구", "서구", "유성구", "중구"
    ],
    "울산광역시": [
        "남구", "동구", "북구", "울주군", "중구"
    ],
    "세종특별자치시": [
        "세종특별자치시"
    ],
    "경기도": [
        "가평군", "고양시", "과천시", "광명시", "광주시",
        "구리시", "군포시", "김포시", "남양주시", "동두천시",
        "부천시", "성남시", "수원시", "시흥시", "안산시",
        "안성시", "안양시", "양주시", "양평군", "여주시",
        "연천군", "오산시", "용인시", "의왕시", "의정부시",
        "이천시", "파주시", "평택시", "포천시", "하남시",
        "화성시"
    ],
    "강원도": [
        "강릉시", "고성군", "동해시", "삼척시", "속초시",
        "양구군", "양양군", "영월군", "원주시", "인제군",
        "정선군", "철원군", "춘천시", "태백시", "평창군",
        "홍천군", "화천군", "횡성군"
    ],
    "충청북도": [
        "괴산군", "단양군", "보은군", "영동군", "옥천군",
        "음성군", "제천시", "증평군", "진천군", "청원군",
        "청주시", "충주시"
    ],
    "충청남도": [
        "계룡시", "공주시", "금산군", "논산시", "당진시",
        "보령시", "부여군", "서산시", "서천군", "아산시",
        "예산군", "천안시", "청양군", "태안군", "홍성군"
    ],
    "전라북도": [
        "고창군", "군산시", "김제시", "남원시", "무주군",
        "부안군", "순창군", "완주군", "익산시", "임실군",
        "장수군", "전주시", "정읍시", "진안군"
    ],
    "전라남도": [
        "강진군", "고흥군", "곡성군", "광양시", "구례군",
        "나주시", "담양군", "목포시", "무안군", "보성군",
        "순천시", "신안군", "여수시", "영광군", "영암군",
        "완도군", "장성군", "장흥군", "진도군", "함평군",
        "해남군", "화순군"
    ],
    "경상북도": [
        "경산시", "경주시", "고령군", "구미시", "군위군",
        "김천시", "문경시", "봉화군", "상주시", "성주군",
        "안동시", "영덕군", "영양군", "영주시", "영천시",
        "예천군", "울릉군", "울진군", "의성군", "청도군",
        "청송군", "칠곡군", "포항시"
    ],
    "경상남도": [
        "거제시", "거창군", "고성군", "김해시", "남해군",
        "밀양시", "사천시", "산청군", "양산시", "의령군",
        "진주시", "창녕군", "창원시", "통영시", "하동군",
        "함안군", "함양군", "합천군"
    ],
    "제주특별자치도": [
        "서귀포시", "제주시"
    ]
}
gugun_combo = ttk.Combobox(search_frame)
gugun_label.pack()

region_combo.bind("<<ComboboxSelected>>", lambda event: gugun_combo.set(""))
gugun_combo.pack()

name_label = tk.Label(window, text="이름으로 검색")
name_label.place(x=200, y = 5)
name_label.configure(bg="#b0e0e6")

name_entry = tk.Entry(window)
name_entry.place(x=185, y=27)
name_entry.configure(width=15)

# 검색 버튼 생성

result_frame = tk.Frame(window)
result_frame.place(x=10, y=120)
result_frame.configure(bg="#b0e0e6")

result_text = tk.Text(result_frame)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
result_text.configure(width = 40, height = 45)

search_button = tk.Button(window, text="검색", command=search_emergency_rooms)
search_button.place(x=140, y=95)
search_button.configure(bg="white")

frame = tk.Frame(window)
frame.place(x=700, y=500)

image_path = "image/tel.png"

target_width = 90
target_height = 90

tk_image = resize_image(image_path, target_width, target_height)

image_label = tk.Label(window, image=tk_image)
image_label.place(x = 800, y = 20)
image_label.bind("<Button-1>", telegram_button_clicked)

# 시/도 선택 시 구/군 목록 업데이트
def update_gugun_options(event):
    selected_region = region_combo.get()
    if selected_region in gugun_dict:
        gugun_options = gugun_dict[selected_region]
        gugun_combo.configure(values=gugun_options)
    else:
        gugun_combo.set("")

region_combo.bind("<<ComboboxSelected>>", update_gugun_options)

window.mainloop()