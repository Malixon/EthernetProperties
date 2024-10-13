import platform
import subprocess
import netifaces
import urllib.request
import socket

import flet as ft


class NetworkSettingsApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Сетевые настройки"
        self.page.window_height = 1000
        self.page.window_height = 800

        # Tabs
        self.tab_info = ft.Text(value="", selectable=True)
        self.site_input = ft.TextField(value="google.com,yandex.ru,8.8.8.8", label="Сайты для пинга")
        self.nas_ip_input = ft.TextField(value="192.168.1.100", label="IP NAS")
        self.port_ip_input = ft.TextField(value="127.0.0.1", label="IP адрес")
        self.port_input = ft.TextField(value="80,443,8080", label="Порты (через запятую)")
        self.check_public = ft.Checkbox(label="Проверить публичный IP", value=False)

        self.setup_layout()

    def setup_layout(self):
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Информация", content=ft.Column(
                    [self.tab_info, ft.ElevatedButton(text="Обновить", on_click=self.display_network_info),
                     ft.ElevatedButton(text="Сохранить", on_click=self.save_network_info)])),
                ft.Tab(text="Пинг", content=ft.Column(
                    [self.site_input, ft.ElevatedButton(text="Пинг сайтов", on_click=self.ping_sites),
                     self.nas_ip_input, ft.ElevatedButton(text="Пинг NAS", on_click=self.ping_nas)])),
                ft.Tab(text="Порты", content=ft.Column([self.port_ip_input, self.port_input, self.check_public,
                                                        ft.ElevatedButton(text="Проверить порты",
                                                                          on_click=self.check_ports)])),
                ft.Tab(text="Сервисы",
                       content=ft.Column([ft.ElevatedButton(text="Проверить сервисы", on_click=self.check_services)])),
            ],
            expand=1
        )
        self.page.add(tabs)
        self.display_network_info()

    def display_network_info(self, e=None):
        # Получаем информацию о сетевых интерфейсах
        info = ""

        info += f"Операционная система: {platform.system()} {platform.release()}\n\n"

        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
            info += f"Публичный IP-адрес: {public_ip}\n\n"
        except Exception as e:
            info += f"Публичный IP-адрес: Не удалось получить (Ошибка: {e})\n\n"

        for interface in netifaces.interfaces():
            info += f"Интерфейс: {interface}\n"
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addresses:
                for address in addresses[netifaces.AF_INET]:
                    info += f"  Приватный IPv4 адрес: {address['addr']}\n"
                    info += f"  Маска подсети: {address['netmask']}\n"
            if netifaces.AF_INET6 in addresses:
                for address in addresses[netifaces.AF_INET6]:
                    info += f"  Приватный IPv6 адрес: {address['addr']}\n"
            if netifaces.AF_LINK in addresses:
                for link_address in addresses[netifaces.AF_LINK]:
                    if link_address['addr']:  # Проверяем, что MAC-адрес не пустой
                        info += f"  MAC адрес: {link_address['addr']}\n"
            info += "\n"

        # Получаем DNS-серверы
        dns_servers = self.get_dns_servers()
        info += f"DNS-серверы: {', '.join(dns_servers)}\n\n"

        self.tab_info.value = info
        self.page.update()

    def save_network_info(self, e=None):
        info = self.tab_info.value
        try:
            with open("network_info.txt", "w") as file:
                file.write(info)
            self.tab_info.value = "Информация сохранена в network_info.txt"
        except PermissionError:
            self.tab_info.value = "Отказано в доступе. Недостаточно прав для сохранения файла."
        except Exception as e:
            self.tab_info.value = f"Не удалось сохранить файл: {str(e)}"
        self.page.update()

    def ping_nas(self, e=None):
        nas_ip = self.nas_ip_input.value
        if not nas_ip:
            self.tab_info.value = "Введите IP-адрес NAS."
            self.page.update()
            return

        try:
            result = subprocess.run(["ping", "-c", "1", nas_ip],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            info = f"Пинг NAS ({nas_ip}):\n{result.stdout}\n"
            self.tab_info.value = info
        except Exception as e:
            info = f"Пинг NAS ({nas_ip}): Не удалось выполнить (Ошибка: {e})\n"
            self.tab_info.value = info
        self.page.update()

    def ping_sites(self, e=None):
        sites = self.site_input.value.split(',')
        if not sites:
            self.tab_info.value = "Введите адреса сайтов/сервисов."
            self.page.update()
            return

        info = ""
        for site in sites:
            site = site.strip()
            try:
                result = subprocess.run(["ping", "-c", "1", site],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)
                info += f"Пинг {site}:\n{result.stdout}\n"
            except Exception as e:
                info += f"Пинг {site}: Не удалось выполнить (Ошибка: {e})\n"
        self.tab_info.value = info
        self.page.update()

    def check_ports(self, e=None):
        ip = self.port_ip_input.value
        ports = [int(p.strip()) for p in self.port_input.value.split(',')]
        check_public = self.check_public.value

        info = ""
        if check_public:
            try:
                public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
                info += f"Проверка портов для публичного IP: {public_ip}\n"
                info = self.check_ports_for_ip(public_ip, ports, info)
            except Exception as e:
                info += f"Не удалось получить публичный IP (Ошибка: {e})\n"

        info += f"\nПроверка портов для IP: {ip}\n"
        info = self.check_ports_for_ip(ip, ports, info)

        self.tab_info.value = info
        self.page.update()

    def check_ports_for_ip(self, ip, ports, info):
        # Проверяем порты для конкретного IP
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            if result == 0:
                info += f"Порт {port} открыт\n"
            else:
                info += f"Порт {port} закрыт\n"
            sock.close()
        return info

    def check_services(self, e=None):
        services = {
            "HTTP": 80,
            "HTTPS": 443,
            "FTP": 21,
            "SSH": 22,
            "SMTP": 25,
            "DNS": 53,
            "SNMP": 161,
            "MySQL": 3306,
            "PostgreSQL": 5432,
            "MongoDB": 27017,
        }

        info = ""
        for service, port in services.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            if result == 0:
                info += f"Сервис {service} доступен на порту {port}\n"
            else:
                info += f"Сервис {service} недоступен на порту {port}\n"
            sock.close()

        self.tab_info.value = info
        self.page.update()

    def get_dns_servers(self):
        dns_servers = []
        if platform.system() == "Windows":
            try:
                output = subprocess.check_output("ipconfig /all").decode("utf-8")
                lines = output.splitlines()
                for line in lines:
                    if "DNS Servers" in line:
                        dns_servers.extend(line.split(":")[1].strip().split(","))
                    elif "DNS-серверы" in line:
                        dns_servers.extend(line.split(":")[1].strip().split(","))
            except Exception as e:
                print(f"Ошибка при получении DNS-серверов (Windows): {e}")
        else:
            try:
                with open("/etc/resolv.conf", "r") as file:
                    for line in file.readlines():
                        if line.startswith("nameserver"):
                            dns_servers.append(line.split()[1])
            except Exception as e:
                print(f"Ошибка при получении DNS-серверов (Unix-like): {e}")

        return [ip for ip in dns_servers if ip]  # Возвращаем только непустые IP адреса


def main(page: ft.Page):
    app = NetworkSettingsApp(page)
    padding = ft.padding.only(left=10, top=20, right=30, bottom=40)


ft.app(target=main)
