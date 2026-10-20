import uuid
from django.db import models
from django.contrib.auth.models import User

class TransportationSurvey(models.Model):
    TRANSPORT_CHOICES = [
        ('walk_bike', 'Jalan Kaki / Sepeda'),
        ('krl_mrt_lrt', 'KRL / MRT / LRT'),
        ('busway', 'Busway / TransJakarta'),
        ('motor_ice', 'Motor Bensin (ICE)'),
        ('car_ice', 'Mobil Bensin (ICE)'),
        ('motor_ev', 'Motor Listrik (EV)'),
        ('car_ev', 'Mobil Listrik (EV)'),
    ]

    # Faktor emisi (kg CO2e per km)
    EMISSION_FACTORS = {
        'walk_bike': 0.000,
        'krl_mrt_lrt': 0.035,
        'busway': 0.089,
        'motor_ice': 0.090,
        'car_ice': 0.190,
        'motor_ev': 0.030,
        'car_ev': 0.070,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transport_surveys')
    
    transport_mode = models.CharField(
        max_length=20, 
        choices=TRANSPORT_CHOICES, 
        default='motor_ice'
    )
    daily_distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True, null=True)
    
    daily_emission_co2 = models.DecimalField(max_digits=8, decimal_places=2, default=0.000)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ambil faktor emisi sesuai moda transportasi
        factor = self.EMISSION_FACTORS.get(self.transport_mode, 0.000)
        distance = float(self.daily_distance_km)
        
        # Hitung emisi untuk segmen moda ini
        self.daily_emission_co2 = distance * factor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.get_transport_mode_display()} ({self.daily_distance_km} km)"


class DailyEmissionLog(models.Model):
    """
    Model snapshot harian untuk kebutuhan grafik dashboard
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_emission_logs')
    date = models.DateField()
    total_emission_co2 = models.DecimalField(max_digits=8, decimal_places=3, default=0.000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.total_emission_co2} kg CO₂"