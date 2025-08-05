from applications.productos.models import Local  # Asegurate que el import apunte bien

def local_actual(request):
    local_id = request.session.get('local_id')
    print('Perdo',request.session.get('local_id'))
    if local_id:
        try:
            print('Local',local_id)
            local = Local.objects.get(id=local_id)
            return {'local_asignado': local.nombre}
        except Local.DoesNotExist:
            pass
    return {'local_asignado': None}