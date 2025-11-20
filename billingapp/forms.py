from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import BILL_TYPE_CHOICES, Bill, Profile, Subscription

User = get_user_model()


class StyledFormMixin:
    """Apply consistent styling classes to form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = (existing + " form-control").strip()


class UserCreationWithProfileForm(StyledFormMixin, UserCreationForm):
    full_name = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        user.is_active = True

        if commit:
            user.save()
            profile = user.profile
            profile.full_name = self.cleaned_data.get("full_name")
            profile.phone = self.cleaned_data.get("phone")
            profile.address = self.cleaned_data.get("address")
            profile.save()

        return user


class BillForm(StyledFormMixin, forms.ModelForm):
    due_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Bill
        fields = ["user", "title", "bill_type", "description", "amount", "due_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bill_type"].widget = forms.Select(choices=BILL_TYPE_CHOICES)


class SubscriptionForm(StyledFormMixin, forms.ModelForm):
    next_renewal_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Subscription
        fields = ["user", "name", "amount", "bill_type", "next_renewal_date", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bill_type"].widget = forms.Select(choices=BILL_TYPE_CHOICES)


class SelfSubscriptionForm(StyledFormMixin, forms.ModelForm):
    next_renewal_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Subscription
        fields = ["name", "amount", "bill_type", "next_renewal_date", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bill_type"].widget = forms.Select(choices=BILL_TYPE_CHOICES)


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "phone", "address"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

