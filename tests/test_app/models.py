from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=255)
    birth = models.DateField('birth date')

    def __str__(self):
        return self.name
