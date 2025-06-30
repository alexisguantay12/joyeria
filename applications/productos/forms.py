from django import forms
from .models import Producto, Categoria

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion','gramos', 'precio_venta',  'categoria']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
    
    # Añadimos algunos campos personalizados
    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.all()  # Asegura que las categorías sean dinámicas
