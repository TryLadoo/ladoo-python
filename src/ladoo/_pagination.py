from __future__ import annotations

from typing import AsyncIterator, Awaitable, Callable, Generator, Generic, Iterator, List, Optional, TypeVar

__all__ = ["AsyncCursorPage", "AsyncPaginator", "SyncCursorPage"]

T = TypeVar("T")


class SyncCursorPage(Generic[T]):
    """One page of a cursor-paginated list.

    Iterating over a page walks every item, fetching later pages as needed.
    Use ``page.data`` for just this page's items.
    """

    data: List[T]
    next_cursor: Optional[str]

    def __init__(
        self,
        data: List[T],
        next_cursor: Optional[str],
        fetch: Callable[[str], SyncCursorPage[T]],
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self._fetch = fetch

    def has_next_page(self) -> bool:
        return bool(self.next_cursor)

    def next_page(self) -> SyncCursorPage[T]:
        if not self.next_cursor:
            raise StopIteration("No more pages; check has_next_page() first")
        return self._fetch(self.next_cursor)

    def iter_pages(self) -> Iterator[SyncCursorPage[T]]:
        page: SyncCursorPage[T] = self
        while True:
            yield page
            if not page.has_next_page():
                return
            page = page.next_page()

    def __iter__(self) -> Iterator[T]:
        for page in self.iter_pages():
            yield from page.data

    def __repr__(self) -> str:
        return f"SyncCursorPage(data=<{len(self.data)} items>, next_cursor={self.next_cursor!r})"


class AsyncCursorPage(Generic[T]):
    """One page of a cursor-paginated list, for :class:`ladoo.AsyncLadoo`.

    ``async for`` over a page walks every item, fetching later pages as needed.
    """

    data: List[T]
    next_cursor: Optional[str]

    def __init__(
        self,
        data: List[T],
        next_cursor: Optional[str],
        fetch: Callable[[str], Awaitable[AsyncCursorPage[T]]],
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self._fetch = fetch

    def has_next_page(self) -> bool:
        return bool(self.next_cursor)

    async def next_page(self) -> AsyncCursorPage[T]:
        if not self.next_cursor:
            raise StopAsyncIteration("No more pages; check has_next_page() first")
        return await self._fetch(self.next_cursor)

    async def iter_pages(self) -> AsyncIterator[AsyncCursorPage[T]]:
        page: AsyncCursorPage[T] = self
        while True:
            yield page
            if not page.has_next_page():
                return
            page = await page.next_page()

    async def __aiter__(self) -> AsyncIterator[T]:
        async for page in self.iter_pages():
            for item in page.data:
                yield item

    def __repr__(self) -> str:
        return f"AsyncCursorPage(data=<{len(self.data)} items>, next_cursor={self.next_cursor!r})"


class AsyncPaginator(Generic[T]):
    """What async ``list()`` methods return.

    ``await`` it for the first page, or ``async for`` over it for every item::

        page = await client.calls.list(limit=50)
        async for call in client.calls.list():
            ...
    """

    def __init__(self, first: Callable[[], Awaitable[AsyncCursorPage[T]]]) -> None:
        self._first = first

    def __await__(self) -> Generator[object, None, AsyncCursorPage[T]]:
        return self._first().__await__()

    async def __aiter__(self) -> AsyncIterator[T]:
        page = await self._first()
        async for item in page:
            yield item
