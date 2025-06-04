import socket
import time
from typing import Optional

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345
ADDR = (SERVER_IP, SERVER_PORT)

def check_server_availability(timeout: int = 1) -> bool:
    """Check if the server is reachable."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto("version".encode(), ADDR)
            data, _ = sock.recvfrom(1024)
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def send_udp_message(message: str, expect_response: bool = True, timeout: int = 1) -> Optional[str]:
    """Send a UDP message to the server and optionally wait for a response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(message.encode(), ADDR)
            
            if expect_response:
                try:
                    data, _ = sock.recvfrom(1024)
                    return data.decode()
                except socket.timeout:
                    return None
            return None
    except Exception as e:
        print(f"Error sending message '{message}': {e}")
        return None

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test(self, name: str, test_func):
        """Run a single test and track results."""
        try:
            test_func()
            print(f"[✓] {name}")
            self.passed += 1
        except AssertionError as e:
            print(f"[✗] {name} - {e}")
            self.failed += 1
        except Exception as e:
            print(f"[✗] {name} - Unexpected error: {e}")
            self.failed += 1
        
        time.sleep(0.1)  # Small delay to ensure server processes requests
    
    def print_summary(self):
        """Print test results summary."""
        print(f"\n✅ {self.passed} passed, ❌ {self.failed} failed")
        return self.failed == 0

def test_version_response():
    """Test that version command returns expected response."""
    response = send_udp_message("version")
    expected = "version=Ken's Key-Value Store 1.0"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_insert_foo_bar():
    """Test inserting foo=bar with no response expected."""
    response = send_udp_message("foo=bar", expect_response=False)
    assert response is None, "Expected no response for insert"

def test_retrieve_foo_after_insert():
    """Test retrieving foo after insert."""
    response = send_udp_message("foo")
    expected = "foo=bar"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_update_foo_baz():
    """Test updating foo=BAZ (overwrite)."""
    response = send_udp_message("foo=BAZ", expect_response=False)
    assert response is None, "Expected no response for update"

def test_retrieve_foo_after_update():
    """Test retrieving foo after update."""
    response = send_udp_message("foo")
    expected = "foo=BAZ"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_insert_key_with_equals_in_value():
    """Test inserting key with = in value (foo=bar=baz)."""
    response = send_udp_message("foo=bar=baz", expect_response=False)
    assert response is None, "Expected no response for insert with = in value"

def test_retrieve_foo_bar_baz():
    """Test retrieving foo=bar=baz."""
    response = send_udp_message("foo")
    expected = "foo=bar=baz"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_insert_empty_key():
    """Test inserting empty key (=val)."""
    response = send_udp_message("=val", expect_response=False)
    assert response is None, "Expected no response for empty key insert"

def test_retrieve_empty_key():
    """Test retrieving empty key."""
    response = send_udp_message("")
    expected = "=val"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_retrieve_missing_key():
    """Test retrieving missing key."""
    response = send_udp_message("nosuchkey")
    expected = "nosuchkey="
    assert response == expected, f"Expected '{expected}', got '{response}'"

def test_ignore_version_insert():
    """Test that version key cannot be overwritten."""
    response = send_udp_message("version=hack", expect_response=False)
    assert response is None, "Expected no response for version insert"

def test_version_unchanged():
    """Test that version remains unchanged after attempted overwrite."""
    response = send_udp_message("version")
    expected = "version=Ken's Key-Value Store 1.0"
    assert response == expected, f"Expected '{expected}', got '{response}'"

def run_tests():
    """Run all tests for the UDP key-value store."""
    # Check server availability
    if not check_server_availability():
        print("❌ Server is not reachable at", ADDR)
        return False
    
    print("🚀 Starting UDP Key-Value Store Tests\n")
    
    runner = TestRunner()
    
    # Run all tests
    test_cases = [
        ("Version response", test_version_response),
        ("Insert foo=bar (no response)", test_insert_foo_bar),
        ("Retrieve foo after insert", test_retrieve_foo_after_insert),
        ("Update foo=BAZ (overwrite)", test_update_foo_baz),
        ("Retrieve foo after update", test_retrieve_foo_after_update),
        ("Insert key with = in value (foo=bar=baz)", test_insert_key_with_equals_in_value),
        ("Retrieve foo=bar=baz", test_retrieve_foo_bar_baz),
        ("Insert empty key (=val)", test_insert_empty_key),
        ("Retrieve empty key", test_retrieve_empty_key),
        ("Retrieve missing key", test_retrieve_missing_key),
        ("Ignore insert to version (version=hack)", test_ignore_version_insert),
        ("Version still unchanged", test_version_unchanged),
    ]
    
    for test_name, test_func in test_cases:
        runner.test(test_name, test_func)
    
    return runner.print_summary()

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)