"""Test database models"""

import pytest
from uuid import uuid4
from datetime import datetime

from kiroku_memory.db.models import Resource, Item, Category, GraphEdge


def test_resource_model():
    """Test Resource model creation"""
    resource = Resource(
        content="Test message",
        source="test:unit",
        metadata_={"key": "value"},
    )
    assert resource.content == "Test message"
    assert resource.source == "test:unit"
    assert resource.metadata_ == {"key": "value"}


def test_item_model():
    """Test Item model creation"""
    item = Item(
        subject="user",
        predicate="likes",
        object="coffee",
        category="preferences",
        confidence=0.9,
        status="active",
    )
    assert item.subject == "user"
    assert item.predicate == "likes"
    assert item.object == "coffee"
    assert item.confidence == 0.9
    assert item.status == "active"


def test_category_model():
    """Test Category model creation"""
    category = Category(
        name="preferences",
        summary="User preferences and settings",
    )
    assert category.name == "preferences"
    assert category.summary == "User preferences and settings"


def test_graph_edge_model():
    """Test GraphEdge model creation"""
    edge = GraphEdge(
        subject="user",
        predicate="knows",
        object="person",
        weight=0.8,
    )
    assert edge.subject == "user"
    assert edge.predicate == "knows"
    assert edge.object == "person"
    assert edge.weight == 0.8
