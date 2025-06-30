import json
from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Modelos de tu aplicación
from .models import Venta, DetalleVenta
from applications.productos.models import Producto,StockLocal  # Ajustá si cambia la ubicación


def no_es_vendedor(user):
    return not user.groups.filter(name='vendedor').exists()

@login_required
def listado_ventas_view(request):
    """
    Muestra el listado de ventas ordenadas de la más reciente a la más antigua.
    """
    if no_es_vendedor(request.user):
        ventas= Venta.objects.all().order_by('-fecha')
    else:
        ventas = Venta.objects.filter(user_made=request.user).order_by('-fecha')
    return render(request, 'ventas/ventas.html', {'ventas': ventas})



@login_required
def agregar_venta_view(request):
    """
    Devuelve el formulario para registrar una nueva venta.
    Se pasa la fecha actual al template.
    """
    return render(request, 'ventas/agregar_venta.html', {
        'fecha_actual': now().date()
    })


@csrf_exempt  # eliminar si ya tenés el token CSRF en el fetch
@login_required
def registrar_venta_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            productos = data.get("productos", [])

            if not productos:
                return JsonResponse({"success": False, "error": "No se enviaron productos."})

            with transaction.atomic():
                venta = Venta.objects.create(user_made=request.user, local=request.user.local)

                for item in productos:
                    try:
                        prod_id = int(item["id"])
                        cantidad = int(item["cantidad"])
                    except (KeyError, ValueError, TypeError):
                        raise Exception("Datos de producto inválidos.")

                    # Buscar producto y stock
                    try:
                        producto = Producto.objects.get(id=prod_id)
                        stock = StockLocal.objects.get(local=venta.local, producto=producto)
                    except Producto.DoesNotExist:
                        raise Exception(f"Producto con ID {prod_id} no existe.")
                    except StockLocal.DoesNotExist:
                        raise Exception(f"No hay stock configurado para {producto.nombre} en este local.")

                    if stock.cantidad < cantidad:
                        raise Exception(f"Stock insuficiente para {producto.nombre}.")
                    print('Elemento aca:',producto.precio_venta)
                    # Descontar stock y guardar
                    stock.cantidad -= cantidad
                    stock.save()  # <--- importante
                    # producto.save() no es necesario salvo que modifiques el producto

                    # Crear detalle de venta
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio_venta,
                        user_made = request.user
                    )

                venta.calcular_total()  # <--- se llama una sola vez al final
                print("Elementos procesados")

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)



@csrf_exempt
@login_required
def eliminar_venta_api(request, id):
    """
    Elimina lógicamente una venta y sus detalles (soft delete),
    devolviendo el stock al local correspondiente.
    """
    if request.method == "POST":
        try:
            with transaction.atomic():
                venta = Venta.objects.get(id=id)
                venta.user_deleted = request.user
                venta.delete()  # Soft delete

                # Devolver stock y eliminar detalles
                detalles = DetalleVenta.objects.filter(venta=venta)
                for detalle in detalles:
                    detalle.user_deleted = request.user
                    detalle.delete()  # Soft delete

                    # Devolver el stock al local
                    stock = StockLocal.objects.get(local=venta.local, producto=detalle.producto)
                    stock.cantidad += detalle.cantidad
                    stock.save()

                return JsonResponse({"success": True})
        except Venta.DoesNotExist:
            return JsonResponse({"success": False, "error": "Venta no encontrada"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)


@login_required
def detalle_venta_view(request, id):
    try:
        venta = Venta.objects.get(id=id)
        detalles = DetalleVenta.objects.filter(venta=venta)
        total_general = sum([d.subtotal for d in detalles])
        
        return render(request, 'ventas/detalle_venta.html', {
            'venta': venta,
            'detalles': detalles,
            'total_general':total_general
        })
    except Venta.DoesNotExist:
        return redirect('ventas_app:listado_ventas')