from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


BASE_URL = "https://www.joinquant.com"


@dataclass
class JoinQuantDraft:
    algorithm_id: str
    user_id: str
    access_control: str
    token: str
    base_capital: str
    start_time: str
    end_time: str
    fontpref: str = "default"
    themepref: str = "ambiance"


CRITICAL_LOG_PATTERNS = [
    r"Traceback",
    r"\s-\sERROR\s+-",
    r"\bException\b",
    r"错误",
    r"异常",
    r"下单失败",
    r"开仓数量不能小于\s*100",
    r"平仓数量不能小于\s*100",
    r"数量为\s*0",
    r"停牌",
    r"涨停",
    r"跌停",
    r"无法成交",
    r"不能买入",
    r"不能卖出",
]


class JoinQuantWebClient:
    """Cookie-authenticated client for JoinQuant web backtests."""

    def __init__(
        self,
        cookie: Optional[str] = None,
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None,
        timeout: int = 30,
        base_url: str = BASE_URL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        final_proxy = proxy or os.getenv("JOINQUANT_PROXY") or ""
        if final_proxy:
            self.session.proxies.update({"http": final_proxy, "https": final_proxy})
        if cookie:
            self.set_cookie(cookie)

    @staticmethod
    def _parse_cookie_string(cookie: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for part in cookie.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            if k.strip():
                result[k.strip()] = v.strip()
        return result

    def set_cookie(self, cookie: str) -> None:
        pairs = self._parse_cookie_string(cookie)
        for k, v in pairs.items():
            self.session.cookies.set(k, v, domain=".joinquant.com", path="/")
        self.session.headers.pop("Cookie", None)

    def get_cookie_string(self) -> str:
        return "; ".join(f"{c.name}={c.value}" for c in self.session.cookies if c.name and c.value)

    @staticmethod
    def load_auth(
        auth_file: Optional[str] = None,
        cookie: Optional[str] = None,
        user_agent: Optional[str] = None,
        require_cookie: bool = True,
    ) -> Dict[str, str]:
        data: Dict[str, str] = {}
        if auth_file and Path(auth_file).exists():
            with open(auth_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        final_cookie = cookie or os.getenv("JOINQUANT_COOKIE") or data.get("cookie") or ""
        final_ua = user_agent or os.getenv("JOINQUANT_USER_AGENT") or data.get("user_agent") or ""
        if require_cookie and not final_cookie:
            raise ValueError("JoinQuant cookie not found. Provide --cookie, JOINQUANT_COOKIE, or --auth-file")
        return {"cookie": final_cookie, "user_agent": final_ua}

    @staticmethod
    def _extract_input_value(text: str, input_name: str, field_name: str) -> str:
        tag_pat = rf"<input\b[^>]*\bname=['\"]{re.escape(input_name)}['\"][^>]*>"
        m = re.search(tag_pat, text, re.I | re.S)
        if not m:
            raise RuntimeError(f"failed to find input tag for {field_name}; cookie may be expired")
        v = re.search(r"\bvalue=['\"]([^'\"]*)['\"]", m.group(0), re.I | re.S)
        if not v:
            raise RuntimeError(f"failed to extract value for {field_name}; page structure changed")
        return v.group(1)

    @staticmethod
    def _parse_json_response(resp: requests.Response) -> Dict[str, Any]:
        text = (resp.text or "").strip()
        if not text:
            return {}
        try:
            return resp.json()
        except Exception:
            try:
                return json.loads(text)
            except Exception as exc:
                raise RuntimeError(f"invalid JSON response: {text[:300]}") from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        resp = self.session.request(method=method, url=f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    def _xhr_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Origin": self.base_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def create_empty_algorithm(self, base_capital: int = 100000) -> JoinQuantDraft:
        resp = self._request(
            "GET",
            "/algorithm/index/new",
            params={"restore": 0, "type": "empty", "baseCapital": base_capital},
            allow_redirects=True,
        )
        if "/user/index/login" in resp.url or "/user/login/index" in resp.url:
            raise RuntimeError("cookie invalid: redirected to login")

        html = resp.text
        token_match = re.search(r'window\.tokenData\s*=\s*\{[^}]*value:\s*"([0-9a-f]+)"', html, re.S)
        if not token_match:
            raise RuntimeError("failed to extract token from edit page; cookie may be expired")

        return JoinQuantDraft(
            algorithm_id=self._extract_input_value(html, "algorithm[algorithmId]", "algorithmId"),
            user_id=self._extract_input_value(html, "algorithm[userId]", "userId"),
            access_control=self._extract_input_value(html, "algorithm[accessControl]", "accessControl"),
            token=token_match.group(1),
            base_capital=self._extract_input_value(html, "backtest[baseCapital]", "backtest[baseCapital]"),
            start_time=self._extract_input_value(html, "backtest[startTime]", "backtest[startTime]"),
            end_time=self._extract_input_value(html, "backtest[endTime]", "backtest[endTime]"),
        )

    def _edit_referer(self, algorithm_id: str, base_capital: int, start_time: str, end_time: str) -> str:
        return (
            f"{self.base_url}/algorithm/index/edit?algorithmId={algorithm_id}&isNew=1&type=empty"
            f"&f=&baseCapital={base_capital}&startTime={start_time}&endTime={end_time}"
        )

    def _build_form(
        self,
        draft: JoinQuantDraft,
        code: str,
        name: str,
        start_time: str,
        end_time: str,
        base_capital: int,
        frequency: str,
        py_version: str,
        mode: str,
    ) -> Dict[str, Any]:
        return {
            "algorithm[algorithmId]": draft.algorithm_id,
            "algorithm[userId]": draft.user_id,
            "algorithm[accessControl]": draft.access_control,
            "backtest[type]": "1" if mode == "save" else "0",
            "algorithm[name]": name,
            "fontpref": draft.fontpref,
            "themepref": draft.themepref,
            "algorithm[code]": base64.b64encode(code.encode("utf-8")).decode("ascii"),
            "backtest[startTime]": start_time,
            "backtest[endTime]": end_time,
            "backtest[baseCapital]": str(base_capital),
            "backtest[frequency]": frequency,
            "backtest[pyVersion]": str(py_version),
            "encrType": "base64",
            "token": draft.token,
            "ajax": "1",
        }

    def save_algorithm(self, draft: JoinQuantDraft, code: str, name: str, start_time: str, end_time: str, base_capital: int, frequency: str = "day", py_version: str = "3") -> Dict[str, Any]:
        data = self._build_form(draft, code, name, start_time, end_time, base_capital, frequency, py_version, "save")
        resp = self._request("POST", "/algorithm/index/save", params={"ajax": 1}, data=data, headers=self._xhr_headers(self._edit_referer(draft.algorithm_id, base_capital, start_time, end_time)))
        payload = self._parse_json_response(resp)
        if payload.get("status") != "0":
            raise RuntimeError(f"save failed: {payload}")
        return payload

    def build_backtest(self, draft: JoinQuantDraft, code: str, name: str, start_time: str, end_time: str, base_capital: int, frequency: str = "day", py_version: str = "3") -> Dict[str, Any]:
        data = self._build_form(draft, code, name, start_time, end_time, base_capital, frequency, py_version, "build")
        resp = self._request("POST", "/algorithm/index/build", params={"ajax": 1}, data=data, headers=self._xhr_headers(self._edit_referer(draft.algorithm_id, base_capital, start_time, end_time)))
        payload = self._parse_json_response(resp)
        if payload.get("status") != "0":
            raise RuntimeError(f"build failed: {payload}")
        return payload

    def get_runtime_info(self, backtest_id: str, token: str) -> Dict[str, Any]:
        resp = self._request("GET", "/algorithm/backtest/runTimeInfo", params={"token": token, "backtestId": backtest_id})
        payload = self._parse_json_response(resp)
        if payload.get("status") != "0":
            raise RuntimeError(f"runTimeInfo failed: {payload}")
        return payload

    def get_stats(self, backtest_id: str, token: str) -> Dict[str, Any]:
        resp = self._request("POST", "/algorithm/backtest/stats", params={"backtestId": backtest_id, "ajax": 1}, data={"undefined": "", "ajax": "1", "token": token})
        payload = self._parse_json_response(resp)
        if payload.get("status") != "0":
            raise RuntimeError(f"stats failed: {payload}")
        return payload

    def get_result_page(self, backtest_id: str, token: str, offset: int = 0) -> Dict[str, Any]:
        resp = self._request("POST", "/algorithm/backtest/result", params={"backtestId": backtest_id, "offset": offset, "userRecordOffset": 0, "ajax": 1}, data={"undefined": "", "ajax": "1", "token": token})
        payload = self._parse_json_response(resp)
        if payload.get("status") != "0":
            raise RuntimeError(f"result failed: {payload}")
        return payload

    def get_log(self, backtest_id: str, token: str, offset: int = 0) -> Dict[str, Any]:
        resp = self._request("POST", "/algorithm/backtest/log", params={"backtestId": backtest_id, "offset": offset, "ajax": 1}, data={"undefined": "", "ajax": "1", "token": token}, headers=self._xhr_headers())
        return self._parse_json_response(resp)

    def wait_until_done(self, backtest_id: str, token: str, timeout_sec: int = 300, poll_interval: float = 2.0) -> Dict[str, Any]:
        start = time.time()
        last_runtime: Dict[str, Any] = {}
        while True:
            last_runtime = self.get_runtime_info(backtest_id, token)
            status = str(last_runtime.get("data", {}).get("status", ""))
            if status == "2":
                return last_runtime
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"backtest timeout ({timeout_sec}s), last runtime={last_runtime}")
            time.sleep(poll_interval)

    def run_backtest(self, code: str, name: str, start_time: str, end_time: str, base_capital: int = 100000, frequency: str = "day", py_version: str = "3", wait_timeout_sec: int = 300, poll_interval: float = 2.0) -> Dict[str, Any]:
        draft = self.create_empty_algorithm(base_capital=base_capital)
        self.save_algorithm(draft, code, name, start_time, end_time, base_capital, frequency, py_version)
        build_payload = self.build_backtest(draft, code, name, start_time, end_time, base_capital, frequency, py_version)
        data_obj = build_payload.get("data", {})
        if not isinstance(data_obj, dict):
            raise RuntimeError(f"build response data type unexpected: {type(data_obj).__name__}, payload={build_payload}")
        backtest_id = data_obj.get("backtestId")
        if not backtest_id:
            raise RuntimeError(f"build response missing backtestId: {build_payload}")
        runtime = self.wait_until_done(backtest_id, draft.token, wait_timeout_sec, poll_interval)
        return {
            "algorithm_id": draft.algorithm_id,
            "backtest_id": backtest_id,
            "token": draft.token,
            "runtime": runtime,
            "stats": self.get_stats(backtest_id, draft.token),
            "result_page_0": self.get_result_page(backtest_id, draft.token, offset=0),
        }

    @staticmethod
    def _extract_algorithm_rows_from_list_html(html: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for tr in re.findall(r'<tr class="algorithm_list">(.*?)</tr>', html, re.S):
            id_match = re.search(r'_algorithmId="([0-9a-f]{32})"', tr)
            name_match = re.search(r'class="black file_name"[^>]*>(.*?)</a>', tr, re.S)
            edit_match = re.search(r"/algorithm/index/edit\?algorithmId=([0-9a-f]{32})", tr)
            if id_match and name_match:
                raw_name = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()
                rows.append({"algorithm_id": id_match.group(1), "edit_algorithm_id": edit_match.group(1) if edit_match else "", "name": unescape(raw_name)})
        return rows

    @staticmethod
    def _extract_list_max_page(html: str) -> int:
        pages = [1]
        for m in re.finditer(r"/algorithm/index/list\?page=(\d+)", html):
            pages.append(int(m.group(1)))
        return max(pages)

    def list_algorithms(self, page: int = 1) -> Dict[str, Any]:
        resp = self._request("GET", "/algorithm/index/list", params={"page": page} if page > 1 else None, allow_redirects=True)
        if "/user/index/login" in resp.url or "/user/login/index" in resp.url:
            raise RuntimeError("cookie invalid: redirected to login")
        return {"page": page, "max_page": self._extract_list_max_page(resp.text), "rows": self._extract_algorithm_rows_from_list_html(resp.text)}

    def list_all_algorithms(self) -> List[Dict[str, str]]:
        first = self.list_algorithms(page=1)
        rows = [dict(r) for r in first.get("rows", [])]
        for page in range(2, int(first.get("max_page", 1) or 1) + 1):
            rows.extend(dict(r) for r in self.list_algorithms(page=page).get("rows", []))
        return rows

    def delete_algorithms(self, algorithm_ids: List[str]) -> Dict[str, Any]:
        ids = [x for x in algorithm_ids if x]
        if not ids:
            return {"status": "0", "code": "00000", "msg": "", "data": {}}
        resp = self._request("POST", "/algorithm/index/del", data={"algorithmId": ",".join(ids)}, headers=self._xhr_headers(f"{self.base_url}/algorithm/index/list"))
        payload = self._parse_json_response(resp)
        if str(payload.get("status")) != "0":
            raise RuntimeError(f"delete failed: {payload}")
        return payload


def extract_joinquant_auth_from_har(har_path: str) -> Dict[str, str]:
    with open(har_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    latest: Optional[Dict[str, Any]] = None
    for entry in data.get("log", {}).get("entries", []):
        req = entry.get("request", {})
        if "www.joinquant.com" not in req.get("url", ""):
            continue
        cookie = ""
        ua = ""
        referer = ""
        for h in req.get("headers", []) or []:
            name = (h.get("name") or "").lower()
            if name == "cookie":
                cookie = h.get("value") or ""
            elif name == "user-agent":
                ua = h.get("value") or ""
            elif name == "referer":
                referer = h.get("value") or ""
        if cookie:
            latest = {"cookie": cookie, "user_agent": ua, "referer": referer, "request_url": req.get("url", ""), "extracted_at": datetime.now().isoformat(timespec="seconds")}
    if not latest:
        raise RuntimeError(f"No JoinQuant cookie found in HAR: {har_path}")
    return latest


def scan_log_text(text: str) -> Dict[str, Any]:
    hits = []
    for pat in CRITICAL_LOG_PATTERNS:
        if re.search(pat, text):
            hits.append(pat)
    return {"has_critical": bool(hits), "matched_patterns": hits}


def extract_log_text(payload: Dict[str, Any]) -> str:
    data = payload.get("data", payload)
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        parts = []
        for key in ("log", "logs", "content", "data", "result"):
            val = data.get(key)
            if isinstance(val, str):
                parts.append(val)
            elif isinstance(val, list):
                parts.extend(str(x) for x in val)
        if parts:
            return "\n".join(parts)
    return json.dumps(payload, ensure_ascii=False)
