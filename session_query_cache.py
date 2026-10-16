import copy
import hashlib
import time

import streamlit as st

from auth import ACCESS_TOKEN_KEY


CACHE_TTL_SECONDS = 15
CACHE_DATA_KEY = "_authenticated_query_cache"
CACHE_SCOPE_KEY = "_authenticated_query_cache_scope"


def _session_scope():
    access_token = st.session_state.get(ACCESS_TOKEN_KEY)
    if not access_token:
        return None

    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def get_cached_query(cache_key, loader, ttl_seconds=CACHE_TTL_SECONDS):
    scope = _session_scope()
    if scope is None:
        return loader()

    if (
        st.session_state.get(CACHE_SCOPE_KEY) != scope
        or CACHE_DATA_KEY not in st.session_state
    ):
        st.session_state[CACHE_SCOPE_KEY] = scope
        st.session_state[CACHE_DATA_KEY] = {}

    cache = st.session_state[CACHE_DATA_KEY]
    now = time.monotonic()
    entry = cache.get(cache_key)
    if entry and now < entry["expires_at"]:
        return copy.deepcopy(entry["value"])

    value = loader()
    cache[cache_key] = {
        "expires_at": now + ttl_seconds,
        "value": copy.deepcopy(value),
    }
    return value


def clear_session_query_cache():
    st.session_state.pop(CACHE_DATA_KEY, None)
