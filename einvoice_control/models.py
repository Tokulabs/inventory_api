from django.db import models

class ApiValues(models.Model):
    id_api = models.PositiveIntegerField()
    name_api = models.CharField(max_length=100)
    type_api = models.CharField(max_length=100)
    name_kiospot = models.CharField(max_length=100, null=True)
    default = models.CharField(max_length=100, null=True)

    def save(self, *args, **kwargs):
        super().save(*args,**kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args,**kwargs)
    
    def __str__(self):
        return self.name