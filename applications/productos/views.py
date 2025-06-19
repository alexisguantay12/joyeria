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
    MovimientoStock, IngresoLote
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

                # Procesar imagen desde webcam (base64)
                webcam_data = request.POST.get('webcam_image')
                if webcam_data:
                    format, imgstr = webcam_data.split(';base64,')
                    ext = format.split('/')[-1]
                    filename = f"{uuid.uuid4()}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    producto.imagen = data

                producto.save()

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
def lista_productos(request):
    es_admin = request.user.is_superuser or request.user.groups.filter(name="administrador").exists()

    if es_admin:
        productos = Producto.objects.all()
    else:
        local = request.user.local
        productos_ids = StockLocal.objects.filter(local=local, cantidad__gt=0).values_list('producto_id', flat=True)
        productos = Producto.objects.filter(id__in=productos_ids)

    productos = Producto.objects.all().order_by('-id')  # El ID más alto primero
    
    return render(request, 'productos.html', {'productos': productos})


@login_required

def buscar_producto_por_codigo(request):
    codigo = request.GET.get("codigo")
    try:
        producto = Producto.objects.get(id=codigo)
        stock = StockLocal.objects.get(producto=producto, local_id=1)
        data = {
            "nombre": producto.nombre,
            "foto": producto.imagen.url if producto.imagen else "",
            "id": producto.id,
            "stock": stock.cantidad,
            "precio": producto.precio_venta
        }
        return JsonResponse({"success": True, "producto": data})
    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado"})
 

@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    es_admin =request.user.is_superuser or request.user.groups.filter(name="administrador").exists()
    
    if es_admin:
        stock_por_local = StockLocal.objects.filter(producto=producto).select_related('local')
    else:
        stock_por_local = StockLocal.objects.filter(producto=producto, local=request.user.local)

    total_stock = sum(s.cantidad for s in stock_por_local)

    return render(request, 'detalle_producto.html', {
        'producto': producto,
        'stock_por_local': stock_por_local,
        'total_stock': total_stock,
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
    return render(request, 'ingreso_mercaderia.html', {
        'fecha_actual': fecha_actual,
        'local_id': local_id,
    })


@login_required
@csrf_exempt
@user_passes_test(no_es_vendedor)
def registrar_ingreso(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get("productos", [])
            local = request.user.local 
            central = Local.objects.get(id=1)

            with transaction.atomic():
                lote = IngresoLote.objects.create(local=local, fecha=timezone.now(),user_made=request.user)

                for item in productos:
                    producto = Producto.objects.get(id=item["id"])
                    cantidad = int(item["cantidad"])

                    MovimientoStock.objects.create(
                        producto=producto,
                        cantidad=cantidad,
                        tipo='ingreso',
                        lote=lote,
                        user_made = request.user
                    )
                    
                    stock_central = StockLocal.objects.get(producto=producto, local=central)
                    stock_central.cantidad -= cantidad 
                    print('Estoy aca stock central',stock_central.cantidad)
                    stock_central.save()
                    stock_local, _ = StockLocal.objects.get_or_create(producto=producto, local=local)
                    stock_local.cantidad += cantidad
                    print('Estoy aca stock local',stock_central.cantidad)
                    stock_local.save()

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})


# ─────────────────────────────────────────────────────────────────────
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
