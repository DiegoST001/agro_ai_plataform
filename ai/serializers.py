from rest_framework import serializers

class OllamaChatRequest(serializers.Serializer):
    prompt = serializers.CharField()

class OllamaChatResponse(serializers.Serializer):
    text = serializers.CharField()