from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render


def _redirect_for_user(user):
    if user.is_staff:
        return redirect("adminportal:dashboard")
    return redirect("customerportal:dashboard")


def home(request):
    if request.user.is_authenticated:
        return _redirect_for_user(request.user)
    return render(request, "index.html")


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_for_user(request.user)

    form = AuthenticationForm(request, data=request.POST or None)
    for field in form.fields.values():
        if hasattr(field.widget, "attrs"):
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_username()}!")
            return _redirect_for_user(user)
        messages.error(request, "Invalid username or password. Please try again.")

    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("login")
