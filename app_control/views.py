from datetime import date

import boto3
from django.db import transaction
from django.db.models.functions.comparison import Coalesce
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from app_control.models import DianResolution, Goals, PaymentTerminal, Provider, PaymentMethod, InventoryMovement, \
    InventoryMovementItem
from inventory_api import settings

from .serializers import (
    GoalSerializer, Inventory, InventorySerializer, InventoryGroupSerializer, InventoryGroup,
    Invoice, InvoiceSerializer, DianSerializer, PaymentTerminalSerializer, ProviderSerializer,
    Customer, CustomerSerializer, InvoiceSimpleSerializer, InventoryMovementSerializer, InventoryMovementItemSerializer
)
from rest_framework.response import Response
from rest_framework import status
from inventory_api.custom_methods import IsAuthenticatedCustom

from inventory_api.utils import CustomPagination, get_query, filter_company, manage_inventories
from django.db.models import Count, Sum, Q

import csv
import codecs
from user_control.views import add_user_activity


class InventoryView(ModelViewSet):
    http_method_names = ('get', 'put', 'delete', 'post')
    queryset = Inventory.objects.select_related("group", "created_by")
    serializer_class = InventorySerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)
        if keyword:
            search_fields = (
                "code", "created_by__fullname", "created_by__email",
                "group__name", "name"
            )
            query = get_query(keyword, search_fields)
            return results.filter(query)
        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})
        add_user_activity(request.user, f"Creó el producto con id: {request.data.get('code')}")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        inventory = self.get_queryset().filter(pk=pk).first()

        if inventory is None:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(inventory, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user, f"Actualizó el producto {inventory.code}. ({request.data})")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        inventory = self.get_queryset().filter(pk=pk).first()
        inventory.delete()
        add_user_activity(request.user, f"Eliminó el producto con id {inventory.code}")
        return Response({"message": "Producto eliminado satisfactoriamente"}, status=status.HTTP_200_OK)

    def toggle_active(self, request, pk=None):
        inventory = self.get_queryset().filter(pk=pk).first()
        if inventory is None:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        inventory.active = not inventory.active
        inventory.save()

        if inventory.active is False:
            add_user_activity(request.user, f"Desactivó el producto {inventory.code}")
        else:
            add_user_activity(request.user, f"Activó el producto {inventory.code}")

        serializer = self.serializer_class(inventory)
        return Response(serializer.data)


class ProviderView(ModelViewSet):
    http_method_names = ('get', 'put', 'delete', 'post')
    queryset = Provider.objects.select_related("created_by")
    serializer_class = ProviderSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        keyword = data.pop("keyword", None)
        data.pop("page", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "nit", "created_by__fullname", "created_by__email", "name"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.order_by('id')

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})
        add_user_activity(request.user, f"Creó el proveedor {request.data.get('name')}")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk):
        request.data.update({"company_id": request.user.company_id})
        provider = self.get_queryset().filter(pk=pk).first()

        if provider is None:
            return Response({'error': 'Proveedor no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user,
                              f"Actualizó el proveedor {request.data.get('name')} ({request.data})")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk):
        provider = self.get_queryset().filter(pk=pk).first()
        provider.delete()
        add_user_activity(request.user, f"Eliminó el proveedor {provider}")
        return Response({"message": "Proveedor eliminado satisfactoriamente"}, status=status.HTTP_200_OK)

    def toggle_active(self, request, pk=None):
        provider = self.get_queryset().filter(pk=pk).first()
        if provider is None:
            return Response({'error': 'Proveedor no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        provider.active = not provider.active
        provider.save()

        if provider.active is False:
            add_user_activity(request.user, f"Desactivó el proveedor {provider}")
        else:
            add_user_activity(request.user, f"Activó el proveedor {provider}")


        serializer = self.serializer_class(provider)
        return Response(serializer.data)


class InventoryMovementView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = InventoryMovement.objects.select_related(
        "created_by").prefetch_related("inventory_movement_items")
    serializer_class = InventoryMovementSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "created_by__fullname", "event_type", "state", "inventory__name"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.order_by('id')

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                request.data.update({"created_by_id": request.user.id})
                request.data.update({"company_id": request.user.company_id})

                if request.data.get("state") != "pending" and request.data.get("state") is not None:
                    raise Exception("El estado inicial del movimiento debe ser pendiente")

                movement_items = request.data.get("inventory_movement_items")
                for item in movement_items:
                    inventory = Inventory.objects.filter(pk=item.get("inventory_id")).first()

                    try:
                        manage_inventories(inventory, item.get("quantity"),
                                           request.data.get("origin"), request.data.get("destination"),
                                           request.data.get("event_type"), mode="check")
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                add_user_activity(request.user,
                                  f"{request.user.fullname} creó un movimiento de inventario "
                                  f"de {request.data.get('event_type')}")
                return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk):
        try:
            with transaction.atomic():
                request.data.update({"company_id": request.user.company_id})
                movement = self.get_queryset().filter(pk=pk).first()

                if movement is None:
                    return Response({'error': 'Movimiento de inventario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

                if movement.state != "pending":
                    return Response({'error': 'Movimiento de inventario ya aprobado o rechazado'},
                                    status=status.HTTP_400_BAD_REQUEST)

                origin = request.data.get("origin")
                destination = request.data.get("destination")
                event_type = request.data.get("event_type")
                movement_items = request.data.get("inventory_movement_items") if request.data.get("inventory_movement_items") \
                    else InventoryMovementItem.objects.filter(inventory_movement_id=movement.id).values()

                for item in movement_items:
                    inventory = Inventory.objects.filter(pk=item.get("inventory_id")).first()
                    try:
                        manage_inventories(inventory, item.get("quantity"),
                                           origin, destination, event_type, mode="check")
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                serializer = self.serializer_class(movement, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    add_user_activity(request.user,
                                      f"{request.user.fullname} actualizó el movimiento de inventario "
                                      f"de {request.data.get('event_type')}")
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk):
        movement = self.get_queryset().filter(pk=pk).first()

        if movement is None:
            return Response({'error': 'Movimiento de inventario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        movement.delete()
        add_user_activity(request.user,
                          f"{request.user.fullname} eliminó el movimiento de inventario "
                          f"de {movement.event_type}")
        return Response({"message": "Movimiento de inventario eliminado satisfactoriamente"},
                        status=status.HTTP_200_OK)

    def change_state(self, request, pk, state):
        try:
            with transaction.atomic():
                movement = self.get_queryset().filter(pk=pk).first()
                
                if state not in ["approve", "reject", "override"]:
                    return Response({'error': 'Tipo de acción no válida'}, status=status.HTTP_400_BAD_REQUEST)

                if movement is None:
                    return Response({'error': 'Movimiento de inventario no encontrado'},
                                    status=status.HTTP_404_NOT_FOUND)
                  
                if state == "approve":
                    try:
                        if movement.state != "pending":
                            return Response({'error': 'Movimiento de inventario ya aprobado o rechazado'},
                                            status=status.HTTP_400_BAD_REQUEST)

                        movement_items = InventoryMovementItem.objects.filter(inventory_movement_id=movement.id,
                                                                              state="pending").all()
                        for item in movement_items:
                            manage_inventories(item.inventory, item.quantity,
                                               movement.origin, movement.destination, movement.event_type,
                                               mode="approval")
                            item.state = "approved"
                            item.save()
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                    movement.state = "approved"
                    movement.save()
                    serializer = self.serializer_class(movement)
                    return Response(serializer.data)
                elif state == "override":
                    if movement.state != "approved":
                        return Response({'error': 'Movimiento no aprobado, solo se puede invalidar movimientos aprobados'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    try:
                        movement_items = InventoryMovementItem.objects.filter(inventory_movement_id=movement.id,
                                                                              state="approved").all()
                        for item in movement_items:
                            if item.state != "approved":
                                return Response(
                                    {'error': 'Movimiento no aprobado, solo se puede invalidar movimientos aprobados'},
                                    status=status.HTTP_400_BAD_REQUEST)
                            manage_inventories(item.inventory, item.quantity,
                                               movement.origin, movement.destination, movement.event_type,
                                               mode="override")
                            item.state = "overrided"
                            item.save()
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                    movement.state = "overrided"
                    movement.save()
                    serializer = self.serializer_class(movement)
                    return Response(serializer.data)
                else:
                    if movement.state != "pending":
                        return Response({'error': 'Movimiento de inventario ya aprobado o rechazado'},
                                        status=status.HTTP_400_BAD_REQUEST)
                    movement.state = "rejected"
                    movement.save()
                    serializer = self.serializer_class(movement)
                    return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def change_state_item(self, request, pk, state):
        try:
            with transaction.atomic():
                movement_item = InventoryMovementItem.objects.filter(pk=pk).first()

                if state not in ["approve", "reject", "override"]:
                    return Response({'error': 'Tipo de acción no válida'}, status=status.HTTP_400_BAD_REQUEST)

                if movement_item is None:
                    return Response({'error': 'Producto de Movimiento no encontrado'},
                                    status=status.HTTP_404_NOT_FOUND)

                movement = InventoryMovement.objects.filter(pk=movement_item.inventory.id, state="pending").first()

                if state == "approve":
                    if movement_item.state != "pending" or movement.state != "pending":
                        return Response({'error': 'Movimiento de inventario ya aprobado o rechazado'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    try:
                        manage_inventories(movement_item.inventory, movement_item.quantity,
                                           movement.origin, movement.destination, movement.event_type,
                                           mode="approval")
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                    movement_item.state = "approved"
                    movement_item.save()
                    serializer = InventoryMovementItemSerializer(movement_item)
                    return Response(serializer.data)
                elif state == "override":
                    if movement_item.state != "approved":
                        return Response({'error': 'Movimiento no aprobado, solo se puede invalidar movimientos aprobados'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    try:
                        print("Overriding changes")
                        manage_inventories(movement_item.inventory, movement_item.quantity,
                                           movement.origin, movement.destination, movement.event_type,
                                           mode="override")
                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                    movement_item.state = "overrided"
                    movement_item.save()
                    serializer = InventoryMovementItemSerializer(movement_item)
                    return Response(serializer.data)
                else:
                    if movement_item.state != "pending" or movement.state != "pending":
                        return Response({'error': 'Movimiento de inventario ya aprobado o rechazado'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    movement_item.state = "rejected"
                    movement_item.save()
                    serializer = InventoryMovementItemSerializer(movement_item)
                    return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = Customer.objects.select_related(
        "created_by")
    serializer_class = CustomerSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        results = filter_company(self.queryset, self.request.user.company_id).filter(**data).order_by('id')

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "document_id", "name"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.order_by('id')

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})
        add_user_activity(request.user, f"Creó el cliente {request.data.get('name')}")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk):
        request.data.update({"company_id": request.user.company_id})
        customer = self.get_queryset().filter(pk=pk).first()

        if customer is None:
            return Response({'error': 'Cliente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user, f"Actualizó el cliente {request.data.get('name')} ({request.data})")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk):
        customer = self.get_queryset().filter(pk=pk).first()
        customer.delete()
        add_user_activity(request.user, f"Eliminó el cliente {customer}")
        return Response({"message": "Cliente eliminado satisfactoriamente"}, status=status.HTTP_200_OK)


class InventoryGroupView(ModelViewSet):
    http_method_names = ('get', 'put', 'delete', 'post')

    queryset = InventoryGroup.objects.select_related(
        "belongs_to", "created_by").prefetch_related("inventories")
    serializer_class = InventoryGroupSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)

        keyword = data.pop("keyword", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data).order_by('id')

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "name"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.annotate(
            total_items=Count('inventories')
        )

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})
        add_user_activity(request.user, f"Creó la categoría {request.data.get('name')}")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        inventory_group = self.get_queryset().filter(pk=pk).first()

        if int(request.data.get("belongs_to_id")) == int(pk):
            print("No puede seleccionar una categoría como su propio padre")
            return Response({'error': 'No puede seleccionar una categoría como su propio padre'},
                            status=status.HTTP_400_BAD_REQUEST)

        if inventory_group is None:
            return Response({'error': 'Categoría no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(inventory_group, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user,
                              f"Actualizó la categoría {request.data.get('name')} ({request.data})")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        inventory_group = self.get_queryset().filter(pk=pk).first()
        inventory_group.delete()
        add_user_activity(request.user, f"Eliminó la categoría {inventory_group}")
        return Response({"message": "Categoría eliminada satisfactoriamente"}, status=status.HTTP_200_OK)

    def toggle_active(self, request, pk=None):
        inventory_group = self.get_queryset().filter(pk=pk).first()

        if inventory_group is None:
            return Response({'error': 'Categoria no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if inventory_group.belongs_to is not None:
            inventory_group_father = self.get_queryset().filter(pk=inventory_group.belongs_to_id).first()
            if inventory_group_father.active == False:
                return Response({'error': 'Categoria padre no está activa'}, status=status.HTTP_400_BAD_REQUEST)

        if not inventory_group.active == False:
            for group in self.get_queryset().filter(belongs_to_id=pk).all():
                group.active = False
                group.save()

        inventory_group.active = not inventory_group.active
        inventory_group.save()

        if inventory_group.active is False:
            add_user_activity(request.user, f"Desactivó la categoría {inventory_group}")
        else:
            add_user_activity(request.user, f"Activó la categoría {inventory_group}")

        serializer = self.serializer_class(inventory_group)
        return Response(serializer.data)


class PaymentTerminalView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = PaymentTerminal.objects.select_related("created_by")
    serializer_class = PaymentTerminalSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)

        keyword = data.pop("keyword", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "name", "account_code"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.order_by('id')

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})
        add_user_activity(request.user, f"Creó el datafono {request.data.get('name')}")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        terminal = self.get_queryset().filter(pk=pk).first()

        if terminal is None:
            return Response({'error': 'Datafono no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(terminal, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user,
                              f"Actualizó el datafono {request.data.get('name')} ({request.data})")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        terminal = self.get_queryset().filter(pk=pk).first()
        add_user_activity(request.user, f"Eliminó el datafono {terminal.name}")
        terminal.delete()
        return Response({"message": "Datafono eliminado satisfactoriamente"}, status=status.HTTP_200_OK)

    def toggle_active(self, request, pk=None):
        terminal = self.get_queryset().filter(pk=pk).first()
        if terminal is None:
            return Response({'error': 'Datafono no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        terminal.active = not terminal.active
        terminal.save()

        if terminal.active is False:
            add_user_activity(request.user, f"Desactivó el datafono {terminal.name}")
        else:
            add_user_activity(request.user, f"Activó el datafono {terminal.name}")

        serializer = self.serializer_class(terminal)
        return Response(serializer.data)


class InvoiceView(ModelViewSet):
    http_method_names = ('get', 'post')
    queryset = Invoice.objects.select_related(
        "created_by", "sale_by", "payment_terminal", "dian_resolution").prefetch_related("invoice_items")
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)

        keyword = data.pop("keyword", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "invoice_number", "dian_resolution__document_number",
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                request.data.update({"company_id": request.user.company_id})
                dian_resolution = filter_company(DianResolution.objects, self.request.user.company_id).filter(
                    active=True).first()
                if not dian_resolution:
                    raise Exception("Necesita una Resolución de la DIAN activa para crear facturas")

                if not request.data.get("sale_by_id"):
                    request.data.update({"sale_by_id": request.user.id})

                request.data.update({"created_by_id": request.user.id})

                new_current_number = dian_resolution.current_number + 1
                dian_resolution_document_number = dian_resolution.id
                dian_resolution.current_number = new_current_number
                dian_resolution.save()

                request.data.update(
                    {"dian_resolution_id": dian_resolution_document_number, "invoice_number": new_current_number})

                invoice = super().create(request, *args, **kwargs)

                add_user_activity(request.user,
                                  f"Creó la factura {request.data.get('invoice_number')}")

                return Response({"message": "Factura creada satisfactoriamente", "data": invoice.data},
                                status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvoiceSimpleListView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination
    serializer_class = InvoiceSimpleSerializer
    queryset = Invoice.objects.select_related(
        "created_by", "sale_by", "payment_terminal", "dian_resolution").prefetch_related("invoice_items")

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)

        keyword = data.pop("keyword", None)
        
        results = filter_company(self.queryset, self.request.user.company_id
                                 ).filter(**data).filter(**data)

        if keyword:
            search_fields = (
                "created_by__fullname", "created_by__email", "invoice_number", "dian_resolution__document_number",
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results.annotate(
            total_sum=Coalesce(Sum("invoice_items__amount", filter=Q(invoice_items__is_gift=False)), 0.0),
            total_sum_usd=Coalesce(Sum("invoice_items__usd_amount", filter=Q(invoice_items__is_gift=False)), 0.0)
        ).order_by('-created_at')


class UpdateInvoiceView(APIView):
    """
    View to override an invoice
    """
    permission_classes = (IsAuthenticatedCustom,)

    def patch(self, request, invoice_number):
        try:
            invoice = filter_company(Invoice.objects, self.request.user.company_id).get(invoice_number=invoice_number)
        except Invoice.DoesNotExist:
            return Response({"error": "Factura no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        if invoice.is_override:
            return Response({"error": "La Factura ya está anulada"}, status=status.HTTP_400_BAD_REQUEST)

        invoice.is_override = True

        for item in invoice.invoice_items.all():
            inventory_item = item.item
            inventory_item.total_in_shops += item.quantity
            inventory_item.save()

        invoice.save()
        add_user_activity(request.user, f"Actualizó la factura {invoice.invoice_number}")
        return Response({"message": "Factura actualizada satisfactoriamente"}, status=status.HTTP_200_OK)


class InvoicePainterView(ModelViewSet):
    http_method_names = ('get',)
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request, *args, **kwargs):
        invoice_number = request.query_params.get("invoice_number", None)
        if not id:
            return Response({"error": "Debe ingresar un número de factura"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            invoice = filter_company(Invoice.objects, self.request.user.company_id).select_related(
                "payment_terminal", "created_by"
            ).filter(invoice_number=invoice_number).first()

            if not invoice:
                return Response({"error": "Factura no encontrada"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(InvoiceSerializer(invoice).data)


class InventoryCSVLoaderView(ModelViewSet):
    http_method_names = ('post',)
    queryset = InventoryView.queryset
    permission_classes = (IsAuthenticatedCustom,)
    serializer_class = InventorySerializer

    def create(self, request, *args, **kwargs):
        try:
            data = request.FILES['data']
        except Exception as e:
            raise Exception("Debe ingresar los productos en un archivo CSV")

        inventory_items = []

        try:
            csv_reader = csv.reader(
                codecs.iterdecode(data, 'utf-8'), delimiter=',')
            next(csv_reader)
            for row in csv_reader:
                if not row[0]:
                    continue
                inventory_items.append({
                    "group_id": int(row[0]),
                    "code": str(row[1]),
                    "name": str(row[2]),
                    "photo": str(row[3]),
                    "total_in_storage": int(row[4]),
                    "total_in_shops": int(row[5]),
                    "selling_price": float(row[6]),
                    "buying_price": float(row[7]),
                    "usd_price": float(row[8]),
                    "provider_id": int(row[9]),
                    "created_by_id": request.user.id,
                    "company_id": request.user.company_id,
                })
        except csv.Error as e:
            raise Exception(e)

        if not inventory_items:
            raise Exception("El archivo CSV no puede estar vacío")

        data_validation = self.serializer_class(
            data=inventory_items, many=True)
        data_validation.is_valid(raise_exception=True)
        data_validation.save()

        add_user_activity(request.user, f"Ingresó productos mediante archivo CSV")

        return Response({
            "success": "Productos creados satisfactoriamente"
        })


class DianResolutionView(ModelViewSet):
    http_method_names = ('get', 'put', 'delete', 'post')
    queryset = DianResolution.objects.all()
    serializer_class = DianSerializer
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        current_resolution = filter_company(self.queryset, self.request.user.company_id).filter(active=True).first()

        if current_resolution is not None and current_resolution.to_date < date.today():
            current_resolution.active = False
            current_resolution.save()

        query_set = filter_company(self.queryset, self.request.user.company_id)
        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        results = query_set.filter(**data)

        if keyword:
            search_fields = (
                "created_by", "document_number", "current_number"
            )
            query = get_query(keyword, search_fields)
            return results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})

        if filter_company(DianResolution.objects.all(), self.request.user.company_id).filter(active=True).exists():
            raise Exception("No puede tener más de una Resolución de la DIAN activa, "
                            "por favor, desactive primero la actual")
        add_user_activity(request.user,
                          f"Creó la resolución '{request.data.get('document_number')}' válida desde '{request.data.get('from_date')}' hasta '{request.data.get('to_date')}'")
        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        dian_res = self.get_queryset().filter(pk=pk).first()

        if dian_res is None:
            return Response({'error': 'Resolución DIAN no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(dian_res, data=request.data)

        if request.data.get("active") is not None and request.data.get("active", True) is True:
            if self.get_queryset().filter(active=True).exists():
                raise Exception("No puede tener más de una Resolución de la DIAN activa, "
                                "por favor, desactive primero la actual")

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        add_user_activity(request.user,
                          f"Actualizó la resolución '{request.data.get('document_number')}' ({request.data})")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        dian_res = self.get_queryset().filter(pk=pk).first()
        add_user_activity(request.user, f"Eliminó la resolución '{dian_res.document_number}'")
        dian_res.delete()
        return Response({"message": "Resolución DIAN eliminada satisfactoriamente"}, status=status.HTTP_200_OK)

    def toggle_active(self, request, pk=None):
        resolution = self.get_queryset().filter(pk=pk).first()
        if resolution is None:
            return Response({'error': 'Resolución DIAN no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        if self.get_queryset().filter(active=True).exists() and resolution.active is False:
            raise Exception("No puede tener más de una Resolución de la DIAN activa, "
                            "por favor, desactive primero la actual")

        if resolution.to_date < date.today():
            raise Exception("No se puede activar una resolución despues de su fecha limite")

        resolution.active = not resolution.active
        resolution.save()
        serializer = self.serializer_class(resolution)

        if resolution.active == True:
            add_user_activity(request.user,
                              f"Activó la resolución '{resolution.document_number}'")
        else:
            add_user_activity(request.user,
                              f"Desactivó la resolución '{resolution.document_number}'")

        return Response(serializer.data)


class GoalView(ModelViewSet):
    http_method_names = ('get', 'post', 'put', 'delete')
    queryset = Goals.objects.all()
    serializer_class = GoalSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def get_queryset(self):
        data = self.request.query_params.dict()
        keyword = data.pop("keyword", None)

        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "created_by", "goal_type"
            )
            query = get_query(keyword, search_fields)
            return results.filter(query)

        return results

    def create(self, request, *args, **kwargs):
        request.data.update({"created_by_id": request.user.id})
        request.data.update({"company_id": request.user.company_id})

        goals = {"diary": "diaria", "weekly": "semanal", "monthly": "mensual", "annual": "anual"}

        add_user_activity(request.user,
                              f"Creó la meta {goals.get(request.data.get('goal_type'))} de {request.data.get('goal_value')}")

        return super().create(request, *args, **kwargs)

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        goal = self.get_queryset().filter(pk=pk).first()

        if goal is None:
            return Response({'error': 'Meta no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(goal, data=request.data)
        if serializer.is_valid():
            goals = {"diary": "diaria", "weekly": "semanal", "monthly": "mensual", "annual": "anual"}

            add_user_activity(request.user,
                              f"Actualizó la meta {goals.get(request.data.get('goal_type'))} de {goal.goal_value} a {request.data.get('goal_value')}")
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        goal = self.get_queryset().filter(pk=pk).first()
        goals = {"diary": "diaria", "weekly": "semanal", "monthly": "mensual", "annual": "anual"}
        add_user_activity(request.user,
                              f"Eliminó la meta {goals.get(request.data.get('goal_type'))} de {request.data.get('goal_value')}")
        goal.delete()
        return Response({"message": "Meta eliminada satisfactoriamente"}, status=status.HTTP_200_OK)


class InvoicePaymentMethodsView(APIView):
    http_method_names = ('post',)
    permission_classes = (IsAuthenticatedCustom,)

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                request.data.update({"company_id": request.user.company_id})
                invoice_id = request.GET.get('invoice_id', None)

                invoice = filter_company(Invoice.objects, self.request.user.company_id).filter(id=invoice_id).first()
                if invoice is None:
                    raise Exception("Factura no encontrada")

                old_payment_methods = []

                for query in invoice.payment_methods.all():
                    old_payment_methods.append(query.name)

                invoice.payment_methods.all().delete()

                payment_methods = request.data.get("payment_methods", None)
                if not payment_methods:
                    raise Exception("Debe ingresar los métodos de pago")

                for method in payment_methods:
                    if (method.get("name") is None or method.get("paid_amount") is None or method.get(
                            "back_amount") is None or method.get("received_amount") is None):
                        raise Exception(
                            "Los métodos de pago deben tener nombre, monto pagado, monto de vuelto y monto recibido")

                new_payment_methods = []
                for method in payment_methods:
                    PaymentMethod.objects.create(
                        invoice_id=invoice_id,
                        name=method.get("name"),
                        paid_amount=method.get("paid_amount"),
                        back_amount=method.get("back_amount"),
                        received_amount=method.get("received_amount"),
                        transaction_code=method.get("transaction_code", None),
                        company_id=request.user.company_id
                    )
                    new_payment_methods.append(method.get("name"))

                add_user_activity(request.user,
                                  f"Actualizó los métodos de pago '{old_payment_methods}' a '{new_payment_methods}'")

                if 'payment_terminal_id' in request.data:
                    invoice.payment_terminal_id = request.data.get("payment_terminal_id", None)
                    invoice.save()

                if 'is_dollar' in request.data:
                    invoice.is_dollar = request.data.get("is_dollar", None)
                    invoice.save()

                return Response(
                    {"message": "Métodos de pago actualizados satisfactoriamente"},
                    status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UploadFileView(ModelViewSet):
    http_method_names = ["post"]
    permission_classes = (IsAuthenticatedCustom,)

    def upload_photo(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No se ha proporcionado un archivo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        aws_access_key = settings.AWS_ACCESS_KEY_ID
        aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
        aws_region = settings.AWS_REGION_NAME

        s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

        try:
            response = s3.generate_presigned_post(
                bucket_name,
                file.name,
                Fields={
                    "Content-Type": file.content_type
                },
                Conditions=[
                    {"Content-Type": file.content_type}
                ],
                ExpiresIn=30000
            )

            data = {
                "final_url": f"{response['url']}{file.name.replace(' ', '+')}",
                "endpoint_data": response
            }
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(data)
