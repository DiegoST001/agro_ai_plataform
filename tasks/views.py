from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Tarea
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def tarea_list(request):
    if request.method == 'GET':
        tareas = Tarea.objects.all()
        data = [{"id": tarea.id, "descripcion": tarea.descripcion, "estado": tarea.estado} for tarea in tareas]
        return JsonResponse(data, safe=False)

    elif request.method == 'POST':
        body = json.loads(request.body)
        nueva_tarea = Tarea.objects.create(
            parcela_id=body['parcela_id'],
            recomendacion_id=body.get('recomendacion_id'),
            tipo=body['tipo'],
            descripcion=body['descripcion'],
            fecha_programada=body['fecha_programada'],
            estado=body['estado'],
            origen=body['origen']
        )
        return JsonResponse({"id": nueva_tarea.id}, status=201)

@csrf_exempt
def tarea_detail(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)

    if request.method == 'GET':
        data = {
            "id": tarea.id,
            "descripcion": tarea.descripcion,
            "estado": tarea.estado
        }
        return JsonResponse(data)

    elif request.method == 'PUT':
        body = json.loads(request.body)
        tarea.descripcion = body.get('descripcion', tarea.descripcion)
        tarea.estado = body.get('estado', tarea.estado)
        tarea.save()
        return JsonResponse({"id": tarea.id})

    elif request.method == 'DELETE':
        tarea.delete()
        return JsonResponse({"message": "Tarea eliminada"}, status=204)