import ssl
import socket
import urllib.parse
from datetime import datetime
import subprocess
from loguru import logger

class ZenSecurityAuditor:
    @staticmethod
    def audit_security_headers(headers: dict) -> dict:
        """Evaluates the presence of critical defensive HTTP headers."""
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        
        headers_to_check = {
            "strict-transport-security": {
                "name": "Strict-Transport-Security (HSTS)",
                "purpose": "Forces HTTPS connections, preventing SSL stripping.",
            },
            "content-security-policy": {
                "name": "Content-Security-Policy (CSP)",
                "purpose": "Restricts resource loading, mitigating XSS.",
            },
            "x-frame-options": {
                "name": "X-Frame-Options",
                "purpose": "Restricts page framing to prevent Clickjacking.",
            },
            "x-content-type-options": {
                "name": "X-Content-Type-Options",
                "purpose": "Prevents MIME-sniffing vulnerabilities.",
            },
            "referrer-policy": {
                "name": "Referrer-Policy",
                "purpose": "Controls referrer information disclosure.",
            }
        }

        report = {}
        for h_key, meta in headers_to_check.items():
            value = normalized_headers.get(h_key)
            report[meta["name"]] = {
                "status": "✅ PASS" if value else "❌ MISSING",
                "value": value or "N/A",
                "purpose": meta["purpose"]
            }
        return report

    @staticmethod
    def audit_tls_connection(hostname: str, port: int = 443) -> dict:
        """Pasively connects to the target's TLS port to inspect certificate validity."""
        context = ssl.create_default_context()
        report = {
            "status": "UNKNOWN",
            "issuer": "N/A",
            "version": "N/A",
            "expires": "N/A",
            "days_left": 0,
            "error": None
        }

        try:
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    
                    exp_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_left = (exp_date - datetime.utcnow()).days

                    report.update({
                        "status": "✅ VALID" if days_left > 0 else "❌ EXPIRED",
                        "issuer": dict(x[0] for x in cert['issuer']).get('organizationName', 'Unknown'),
                        "version": ssock.version(),
                        "cipher": cipher[0],
                        "bits": cipher[2],
                        "expires": cert['notAfter'],
                        "days_left": days_left
                    })
        except Exception as e:
            report["status"] = "❌ FAILED"
            report["error"] = str(e)
            
        return report

    @staticmethod
    def audit_dns_records(domain: str) -> dict:
        """TXT record lookups with graceful fallback if nslookup is missing in Termux"""
        report = {
            "SPF (Sender Policy Framework)": {"status": "❌ MISSING", "record": "N/A"},
            "DMARC (Domain-based Message Authentication)": {"status": "❌ MISSING", "record": "N/A"}
        }

        try:
            # Check SPF via nslookup
            cmd = ["nslookup", "-type=TXT", domain]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "v=spf1" in line:
                        report["SPF (Sender Policy Framework)"] = {
                            "status": "✅ CONFIGURED",
                            "record": line.strip()
                        }

            # Check DMARC via nslookup
            cmd_dmarc = ["nslookup", "-type=TXT", f"_dmarc.{domain}"]
            res_dmarc = subprocess.run(cmd_dmarc, capture_output=True, text=True, timeout=5)
            if res_dmarc.returncode == 0:
                for line in res_dmarc.stdout.splitlines():
                    if "v=DMARC1" in line:
                        report["DMARC (Domain-based Message Authentication)"] = {
                            "status": "✅ CONFIGURED",
                            "record": line.strip()
                        }
                        
        except FileNotFoundError:
            # GRACEFUL FALLBACK: If Termux is missing dnsutils
            logger.warning("⚠️ 'nslookup' is missing. Run 'pkg install dnsutils' in Termux to enable DNS Auditing.")
            report["SPF (Sender Policy Framework)"]["status"] = "❌ UNKNOWN (Install dnsutils)"
            report["DMARC (Domain-based Message Authentication)"]["status"] = "❌ UNKNOWN (Install dnsutils)"
        except Exception as e:
            logger.error(f"DNS query error: {e}")

        return report

    @staticmethod
    def get_audit_endpoints(base_url: str) -> list:
        """Assembles and returns full, valid audit URLs with their signatures"""
        parsed = urllib.parse.urlparse(base_url)
        root_url = f"{parsed.scheme}://{parsed.netloc}/"
        
        audit_targets = [
            {"path": ".env", "desc": "Raw Environment Variables (DB passwords, API keys)", "sig": "DB_"},
            {"path": ".git/config", "desc": "Git Configuration (Exposes internal repo paths)", "sig": "[core]"},
            {"path": "wp-config.php.bak", "desc": "WordPress Config Backup", "sig": "define("},
            {"path": "config.json", "desc": "Node/Application Config File", "sig": "{"},
            {"path": "robots.txt", "desc": "Search Engine Directives", "sig": "User-agent:"}
        ]
        
        # FIXED: Correctly compile and return the "url" and "signature" keys
        compiled_requests = []
        for target in audit_targets:
            compiled_requests.append({
                "url": urllib.parse.urljoin(root_url, target["path"]),
                "desc": target["desc"],
                "signature": target["sig"]
            })
        return compiled_requests
