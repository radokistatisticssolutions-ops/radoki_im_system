from django import forms
from .models import ReferralReward


class ReferralRewardClaimForm(forms.Form):
    """Form for claiming available referral rewards"""
    
    reward_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        self.reward = kwargs.pop('reward', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        if self.reward:
            if not self.reward.can_claim():
                raise forms.ValidationError(
                    "This reward cannot be claimed. It may have expired or already been claimed."
                )
        
        return cleaned_data


class ReferralFeedbackForm(forms.Form):
    """Optional form for referral feedback"""
    
    RATING_CHOICES = [
        (1, '⭐ Poor'),
        (2, '⭐⭐ Fair'),
        (3, '⭐⭐⭐ Good'),
        (4, '⭐⭐⭐⭐ Very Good'),
        (5, '⭐⭐⭐⭐⭐ Excellent'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(),
        required=True,
        label="How would you rate our referral program?"
    )
    
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Share your thoughts about the referral program...'
        }),
        required=False,
        label="Additional feedback (optional)"
    )
    
    def clean_feedback(self):
        feedback = self.cleaned_data.get('feedback', '')
        if feedback and len(feedback) > 500:
            raise forms.ValidationError("Feedback must be 500 characters or less.")
        return feedback
