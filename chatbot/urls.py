from django.urls import path
from .views import ChatbotView, ChatHistoryView, CropDataView, ClearChatHistoryView, VoiceChatView

urlpatterns = [
    path('', ChatbotView.as_view(), name='chatbot'),
    path('voice/', VoiceChatView.as_view(), name='chatbot-voice'),
    path('history/', ChatHistoryView.as_view(), name='chatbot-history'),
    path('crop-data/', CropDataView.as_view(), name='chatbot-crop-data'),
    path('clear-history/', ClearChatHistoryView.as_view(), name='chatbot-clear-history'),
]
