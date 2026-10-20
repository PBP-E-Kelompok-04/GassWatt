from django import forms
from .models import TransportationSurvey

class TransportationSurveyForm(forms.ModelForm):
    class Meta:
        model = TransportationSurvey
        fields = ['transport_mode', 'daily_distance_km', 'notes']
        labels = {
            'transport_mode': 'Moda Transportasi',
            'daily_distance_km': 'Jarak Tempuh Harian (km)',
            'notes': 'Keterangan Rute / Segmen Perjalanan',
        }
        widgets = {
            'transport_mode': forms.Select(attrs={'class': 'form-select'}),
            'daily_distance_km': forms.NumberInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Contoh: 3.5', 
                'step': '0.1', 
                'min': '0'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Contoh: Rumah ke Stasiun'
            }),
        }