from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction

from .forms import ProductoForm
from .models import (
    Producto, StockLocal, Local,
    MovimientoStock, IngresoLote,ImagenProducto
)

import os
import uuid
import json
import base64
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont


# ─────────────────────────────────────────────────────────────────────
# Permisos
# ─────────────────────────────────────────────────────────────────────

def no_es_vendedor(user):
    return not user.groups.filter(name='vendedor').exists()

# ─────────────────────────────────────────────────────────────────────
# PRODUCTO: Crear, listar, buscar, ver detalle
# ─────────────────────────────────────────────────────────────────────
from django.contrib.staticfiles import finders
@login_required
@user_passes_test(no_es_vendedor)
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                producto = form.save(commit=False)
                
                producto.save()

                # Procesar imágenes desde la cámara (base64)
                webcam_images_data = request.POST.get('webcam_images')
                print('Muestra', webcam_images_data)
                if webcam_images_data:
                    try:
                        # Decodificar las imágenes base64
                        print('Muestra', webcam_images_data) 
                        webcam_images = json.loads(webcam_images_data)
                        for img_data in webcam_images:
                            format, imgstr = img_data.split(';base64,')
                            ext = format.split('/')[-1]
                            filename = f"{uuid.uuid4()}.{ext}"
                            data = ContentFile(base64.b64decode(imgstr), name=filename)

                            # Crear una instancia de ImagenProducto y asociarla al producto
                            imagen_producto = ImagenProducto(producto=producto, imagen=data)
                            imagen_producto.save()

                    except Exception as e:
                        print(f"Error al procesar las imágenes: {e}")


                # Crear código de barras
                barcode_dir = os.path.join(settings.MEDIA_ROOT, 'barcodes')
                os.makedirs(barcode_dir, exist_ok=True)

                codigo = str(producto.id).zfill(12)
                barcode_path = os.path.join(barcode_dir, f'{codigo}')

                options = {
                    "module_width": 0.4,
                    "module_height": 15.0,
                    "write_text": False,
                    "quiet_zone": 6.0
                }

                EAN = barcode.get_barcode_class('code128')
                ean = EAN(codigo, writer=ImageWriter())
                ean.save(barcode_path, options)

                producto.codigo_barras = f'barcodes/{codigo}.png'
                producto.save()

                # Agregar texto debajo del código de barras
                img = Image.open(f"{barcode_path}.png")
                new_height = img.height + 40
                new_img = Image.new("RGB", (img.width, new_height), "white")
                new_img.paste(img, (0, 0))
 
                font_path = finders.find('fonts/DejaVuSans.ttf')
                font = ImageFont.truetype(font_path, 30)
                draw = ImageDraw.Draw(new_img)

                char_spacing = 21
                char_widths = [draw.textsize(c, font=font)[0] for c in codigo]
                total_width = sum(char_widths) + char_spacing * (len(codigo) - 1)
                x_text = (img.width - total_width) // 2
                y_text = img.height + 5
                x_cursor = x_text

                for c in codigo:
                    draw.text((x_cursor, y_text), c, font=font, fill="black")
                    x_cursor += draw.textsize(c, font=font)[0] + char_spacing

                new_img.save(f"{barcode_path}.png")

                # Registrar stock inicial en local 1
                try:
                    cantidad = int(request.POST.get("cantidad", 0))
                except ValueError:
                    cantidad = 0
                print('CANTIDAD',cantidad)
                local = Local.objects.get(id=1)
                stock_obj, _ = StockLocal.objects.get_or_create(producto=producto, local=local)
                stock_obj.cantidad += cantidad
                stock_obj.save()

                imprimir_etiquetas = request.POST.get('imprimir') == 'true'
                print('IMPRIMIR',imprimir_etiquetas)
                if imprimir_etiquetas and cantidad > 0:
                    return render(request, 'imprimir_etiqueta.html', {
                        'etiqueta_url': producto.codigo_barras.url,
                        'cantidad': cantidad,
                        'repeticiones': range(cantidad)  # 👈 creamos una lista de repeticiones
                    })

            return redirect('products_app:productos')
    else:
        form = ProductoForm()

    return render(request, 'agregar_producto.html', {'form': form})


@csrf_exempt
@login_required
def eliminar_producto_api(request, id):
    """
    Elimina lógicamente una venta y sus detalles (soft delete),
    devolviendo el stock al local correspondiente.
    """
    if request.method == "POST":
        try:
            with transaction.atomic():
                producto = Producto.objects.get(id=id)
                producto.user_deleted = request.user
                producto.delete()  # Soft delete
                # Devolver stock y eliminar detalles 

                return JsonResponse({"success": True})
        except Venta.DoesNotExist:
            return JsonResponse({"success": False, "error": "Venta no encontrada"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)




@login_required
@user_passes_test(no_es_vendedor)
def imprimir_etiquetas(request, producto_id):
    cantidad = int(request.GET.get("cantidad", 0))
    producto = get_object_or_404(Producto, id=producto_id)

    if cantidad > 0 and producto.codigo_barras:
        return render(request, 'impresion_etiquetas.html', {
            'etiqueta_url': producto.codigo_barras.url,
            'cantidad': cantidad,
            'repeticiones': range(cantidad),
            'producto_id':producto.id
        })

    return redirect('products_app:detalle_producto', producto_id=producto.id)


@login_required
@user_passes_test(no_es_vendedor)
def lista_productos(request):

    productos = Producto.objects.all().order_by('-id')  # El ID más alto primero
    
    return render(request, 'productos.html', {'productos': productos})


@login_required
def buscar_producto_por_codigo_venta(request):
    codigo = request.GET.get("codigo")
    try:
        producto = Producto.objects.get(id=codigo) 
        # Intentamos obtener el stock
        try:
            stock = StockLocal.objects.get(producto=producto, local=request.user.local)
            cantidad_stock = stock.cantidad
        except StockLocal.DoesNotExist:
            cantidad_stock = 0
        fotos = [img.imagen.url for img in producto.imagenes.all()]
        foto_principal = fotos[0] if fotos else ""
        data = {
            "nombre": producto.nombre,
            "foto": foto_principal,
            "id": producto.id,
            "stock": cantidad_stock,
            "precio": producto.precio_venta
        }
        return JsonResponse({"success": True, "producto": data})
    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado"})
 
@login_required

def buscar_producto_por_codigo(request):
    codigo = request.GET.get("codigo")
    local_id= request.GET.get("local_id")
    try:
        producto = Producto.objects.get(id=codigo)

        # Si local_id es "0" o "" asumimos que es Central (puedes adaptar la lógica)
        if not local_id or local_id in ["0", ""]:
            local = Local.objects.get(nombre="Central")  # O usa tu lógica para obtener Central
        else:
            local = Local.objects.get(id=local_id)

        # Intentamos obtener el stock
        try:
            stock = StockLocal.objects.get(producto=producto, local=local)
            cantidad_stock = stock.cantidad
        except StockLocal.DoesNotExist:
            cantidad_stock = 0
        fotos = [img.imagen.url for img in producto.imagenes.all()]
        foto_principal = fotos[0] if fotos else ""
        data = {
            "nombre": producto.nombre,
            "foto": foto_principal,
            "id": producto.id,
            "stock": cantidad_stock,
            "precio": producto.precio_venta
        }
        return JsonResponse({"success": True, "producto": data})
    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado"})
 
from applications.ventas.models import DetalleVenta  # Asegurate de importar el modelo

@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    es_admin = request.user.is_superuser or request.user.groups.filter(name="administrador").exists()
    
    if es_admin:
        stock_por_local = StockLocal.objects.filter(producto=producto).select_related('local')
    else:
        stock_por_local = StockLocal.objects.filter(producto=producto, local=request.user.local)

    total_stock = sum(s.cantidad for s in stock_por_local)

    # Obtener ventas relacionadas a este producto
    ventas = DetalleVenta.objects.filter(producto=producto).select_related('venta__local', 'venta__user_made').order_by('-venta__fecha')

    return render(request, 'detalle_producto.html', {
        'producto': producto,
        'stock_por_local': stock_por_local,
        'total_stock': total_stock,
        'ventas': ventas,  # nuevo contexto para el modal
    })

@login_required
def imprimir_codigo(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'imprimir_codigo.html', {'producto': producto})


# ─────────────────────────────────────────────────────────────────────
# INGRESO DE MERCADERÍA
# ─────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(no_es_vendedor)
def ingreso_mercaderia(request):
    local_id = request.GET.get("local_id") or 1
    fecha_actual = timezone.now().strftime("%d/%m/%Y")
    locales = Local.objects.exclude(nombre="Central")
    return render(request, 'ingreso_mercaderia.html', {
        'fecha_actual': fecha_actual,
        'local_id': local_id,
        'locales':locales
    })


@login_required
@csrf_exempt
@user_passes_test(no_es_vendedor)  # Asegúrate de que esta func existe
def registrar_ingreso(request):
    """Registrar una transferencia de productos entre Central y un Local involucrado."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        productos = data.get("productos", [])
        local_id = data.get("local_id")
        tipo = data.get("tipo")

        if not local_id or not tipo:
            return JsonResponse({"success": False, "error": "Faltan datos requeridos (local_id, tipo)."}, status=400)

        # Verificación de existencia de locales
        try:
            local_involucrado = Local.objects.get(id=local_id)
            central = Local.objects.get(nombre="Central")
        except Local.DoesNotExist:
            return JsonResponse({"success": False, "error": "Local no encontrado."}, status=404)

        # Crear el lote de ingreso
        with transaction.atomic():
            lote = IngresoLote.objects.create(local=local_involucrado, tipo=tipo, fecha=timezone.now(), user_made=request.user)

            for item in productos:
                producto_id = item.get("id")
                cantidad = int(item.get("cantidad", 0))
                if cantidad <= 0:
                    return JsonResponse({"success": False, "error": f"Cantidad no válida para producto ID {producto_id}."}, status=400)

                producto = Producto.objects.filter(id=producto_id).first()
                if not producto:
                    return JsonResponse({"success": False, "error": f"Producto ID {producto_id} no encontrado."}, status=404)

                # Definir local de origen y destino según el tipo de operación
                if tipo == "entrada":
                    origen = central
                    destino = local_involucrado
                else:
                    origen = local_involucrado
                    destino = central

                # Verificación de stock en el local de origen
                stock_origen, _ = StockLocal.objects.get_or_create(producto=producto, local=origen, defaults={'cantidad': 0})
                if stock_origen.cantidad < cantidad:
                    return JsonResponse({"success": False, "error": f"No hay suficiente stock de {producto.nombre} en el local {origen.nombre}. Stock actual: {stock_origen.cantidad}"}, status=400)

                # Crear movimiento de stock
                MovimientoStock.objects.create(
                    producto=producto,
                    cantidad=cantidad,
                    lote=lote,
                    user_made=request.user
                )
                # Actualizar stock origen
                stock_origen.cantidad -= cantidad
                stock_origen.save()

                # Actualizar stock destino
                stock_destino, _ = StockLocal.objects.get_or_create(producto=producto, local=destino, defaults={'cantidad': 0})
                stock_destino.cantidad += cantidad
                stock_destino.save()

        return JsonResponse({"success": True}, status=200)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
# CONSULTAS DE INGRESOS
# ─────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(no_es_vendedor)
def lista_ingresos(request):
    ingresos = IngresoLote.objects.all().order_by('-fecha')
    return render(request, 'ingresos.html', {'ingresos': ingresos})


@login_required
@user_passes_test(no_es_vendedor)
def detalle_ingreso(request, ingreso_id):
    ingreso = get_object_or_404(IngresoLote, id=ingreso_id)
    productos = ingreso.movimientos.all()

    return render(request, 'detalle_ingreso.html', {
        'ingreso': ingreso,
        'productos': productos,
    })


from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import IngresoLote
from datetime import timedelta
from django.utils import timezone

@login_required
@user_passes_test(no_es_vendedor)
def eliminar_ingreso(request, ingreso_id):
    """Elimina un IngresoLote y revierte los cambios de stock, si no pasaron 30 minutos."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

    lote = get_object_or_404(IngresoLote, id=ingreso_id)

    # ✅ Verificar si pasaron más de 30 minutos
    tiempo_limite = lote.fecha + timedelta(minutes=0)
    if timezone.now() > tiempo_limite:
        return JsonResponse({
            "success": False,
            "error": "Eliminacion restringida debido a que paso mas de 30 minutos de su creacion ."
        }, status=403)

    try:
        central = Local.objects.get(nombre="Central")
    except Local.DoesNotExist:
        return JsonResponse({"success": False, "error": "Local 'Central' no encontrado."}, status=404)

    try:
        with transaction.atomic():
            movimientos = MovimientoStock.objects.filter(lote=lote)

            for movimiento in movimientos:
                producto = movimiento.producto
                cantidad = movimiento.cantidad
                local_involucrado = lote.local

                if lote.tipo == "entrada":
                    stock_local_involucrado = StockLocal.objects.get(producto=producto, local=local_involucrado)
                    stock_central = StockLocal.objects.get(producto=producto, local=central)

                    if stock_local_involucrado.cantidad < cantidad:
                        raise ValueError(f"No hay suficiente stock en {local_involucrado.nombre} para revertir producto {producto.nombre}")

                    stock_local_involucrado.cantidad -= cantidad
                    stock_local_involucrado.save()

                    stock_central.cantidad += cantidad
                    stock_central.save()

                else:
                    stock_central = StockLocal.objects.get(producto=producto, local=central)
                    stock_local_involucrado = StockLocal.objects.get(producto=producto, local=local_involucrado)

                    if stock_central.cantidad < cantidad:
                        raise ValueError(f"No hay suficiente stock en Central para revertir producto {producto.nombre}")

                    stock_central.cantidad -= cantidad
                    stock_central.save()

                    stock_local_involucrado.cantidad += cantidad
                    stock_local_involucrado.save()

            movimientos.delete()
            lote.delete()

            return JsonResponse({"success": True, "message": f"Ingreso {lote.id} eliminado y stock revertido correctamente."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"No se pudo eliminar el ingreso. Error: {str(e)}"}, status=500)
