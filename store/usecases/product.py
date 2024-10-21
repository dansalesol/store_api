from typing import List
from uuid import UUID

import pymongo
from bson import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from store.core.exceptions import InternalServerError, NotFoundException
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import ProductIn, ProductOut, ProductUpdate, ProductUpdateOut


class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def create(self, body: ProductIn) -> ProductOut:
        product_model = ProductModel(**body.model_dump())
        await self.collection.insert_one(product_model.model_dump())

        return ProductOut(**product_model.model_dump())

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductOut(**result)

    async def query(self) -> List[ProductOut]:
        return [ProductOut(**item) async for item in self.collection.find()]

    async def update(self, id: UUID, body: ProductUpdate) -> ProductUpdateOut:
        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": body.model_dump(exclude_none=True)},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        return ProductUpdateOut(**result)

    async def filtered_query(
        self, min_price: float = 5000, max_price: float = 8000
    ) -> List[ProductOut]:
        try:
            min_price_decimal = Decimal128(str(min_price))
            max_price_decimal = Decimal128(str(max_price))

            cursor = self.collection.find(
                {"price": {"$gt": min_price_decimal, "$lt": max_price_decimal}}
            )

            products = [ProductOut(**product) async for product in cursor]

            return products
        except Exception as e:
            print(f"Error occurred while querying products: {e}")
            raise InternalServerError()

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        result = await self.collection.delete_one({"id": id})

        return True if result.deleted_count > 0 else False


product_usecase = ProductUsecase()
