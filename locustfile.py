from locust import HttpUser, task, between

class BoutiqueUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def view_frontpage(self):
        self.client.get("/")

    @task(1)
    def browse_product(self):
        self.client.get("/product/OLJCESPC7Z")