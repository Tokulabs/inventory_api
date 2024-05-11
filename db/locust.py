import time
from locust import HttpUser, task, between


class WebsiteUser(HttpUser):
    wait_time = between(1, 5)
    host = 'https://djangoappinventory.onrender.com'

    def on_start(self):
        response = self.client.post("user/login", json={"email":"ndfranco2@gmail.com", "password":"miclave"})
        if response.status_code != 200:
            print("Failed to authenticate")
            self.environment.runner.quit()

    # @task
    # def index_page(self):
    #     self.client.get(url="/hello")

    #Shop
    @task
    def shop(self):
        self.client.get(url="/app/shop")#POST
        self.client.get(url="/app/shop?page=3")#GET
        self.client.get(url="/app/shop/2")#DELETE

    #Group
    @task
    def group(self):
        self.client.get(url="/app/group")#POST
        self.client.get(url="/app/group?keyword=1")#GET
        self.client.get(url="/app/group/4")#DELETE

    #Inventory
    @task
    def inventory(self):
        self.client.get(url="/app/inventory")#POST
        self.client.get(url="/app/inventory?page=1")#GET
        self.client.get(url="/app/inventory/2")#DELETE

    @task
    def dian_res(self):
        self.client.get(url="/app/dian-resolution")#POST
        self.client.get(url="/app/dian-resolution")#GET
        self.client.get(url="/app/dian-resolution/2")#DELETE