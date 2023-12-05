"""Fichier UserProfile.users.forms.py les formulaires utilisateur"""
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CustomUserCreationForm(UserCreationForm):
    """
    Formulaire pour la création d’un utilisateur.
    """

    class Meta(UserCreationForm.Meta):
        """
        Meta information.
        """

        fields = UserCreationForm.Meta.fields + ("first_name", "last_name", "email")

    def save(self, commit=True):
        """
        Fonction de sauvegarde.
        """
        user = super(CustomUserCreationForm, self).save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Formulaire pour la modification de user
    """

    class Meta(UserChangeForm.Meta):
        """
        Meta information.
        """

        fields = ("email", "first_name", "last_name", "password")
