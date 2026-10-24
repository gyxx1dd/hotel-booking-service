from rest_framework import serializers

from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "type", "status", "money_to_pay", "session_url")
        read_only_fields = fields
