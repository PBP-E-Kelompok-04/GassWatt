from django import forms
from .models import SavedLocation


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
