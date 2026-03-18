from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Custom manager that uses email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_role", "admin")
        extra_fields.setdefault("account_status", "approved")
        extra_fields.setdefault("full_name", "Admin")
        extra_fields.setdefault("phone", "0000000000")
        extra_fields.setdefault("gender", "Prefer not to say")
        extra_fields.setdefault("hostel_name", "N/A")
        extra_fields.setdefault("town", "N/A")

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)