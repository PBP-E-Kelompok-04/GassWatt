from django import forms
from .models import TransportationSurvey, SavedLocation

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

class LocationForm(forms.ModelForm):
    class Meta:
        model = SavedLocation
        fields = ["name", "latitude", "longitude"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Nama lokasi wajib diisi.")
        return name

    def clean_latitude(self):
        value = self.cleaned_data["latitude"]
        if not -90 <= value <= 90:
            raise forms.ValidationError("Latitude harus antara -90 dan 90.")
        return round(value, 6)

    def clean_longitude(self):
        value = self.cleaned_data["longitude"]
        if not -180 <= value <= 180:
            raise forms.ValidationError("Longitude harus antara -180 dan 180.")
        return round(value, 6)


class LocationRenameForm(forms.ModelForm):
    class Meta(LocationForm.Meta):
        fields = ["name"]
