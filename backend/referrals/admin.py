from django.contrib import admin
from .models import ReferralProfile, Referral, WalletReward, WalletLedgerEntry

admin.site.register(ReferralProfile)
admin.site.register(Referral)
admin.site.register(WalletReward)
admin.site.register(WalletLedgerEntry)
