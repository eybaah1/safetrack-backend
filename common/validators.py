from django.core.validators import MinValueValidator, MaxValueValidator


latitude_validators = [MinValueValidator(-90), MaxValueValidator(90)]
longitude_validators = [MinValueValidator(-180), MaxValueValidator(180)]