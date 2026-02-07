#!/usr/bin/env python3
"""
GCP Service Account Setup Script for Car Buyer Assist RAG Application

This script automates the setup of a GCP service account with proper permissions
for accessing Vertex AI services including embedding models and LLMs.

Prerequisites:
- User must be authenticated via 'gcloud auth login'
- User must have Owner or Editor role on the GCP project

Usage:
    python setup_gcp_sa.py
    python setup_gcp_sa.py --skip-enable-apis   # If you get permission errors, enable APIs manually in Console first
"""

import argparse
import os
import sys
import json

# Fix Windows console encoding for Unicode symbols (✓, ✗)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
import re
from pathlib import Path
from typing import Optional, Tuple

# Google Cloud SDK imports
try:
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import iam_admin_v1
    from google.cloud import resourcemanager_v3
    from google.cloud import service_usage_v1
    from google.api_core import exceptions as google_exceptions
except ImportError as e:
    print(f"Error: Missing required Google Cloud SDK libraries.")
    print(f"Please install dependencies: pip install -r requirements.txt")
    print(f"Details: {e}")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class GCPServiceAccountSetup:
    """Handles GCP service account setup and configuration"""
    
    def __init__(self, skip_enable_apis: bool = False):
        self.project_id: Optional[str] = None
        self.skip_enable_apis = skip_enable_apis
        self.sa_name: Optional[str] = None
        self.sa_display_name: Optional[str] = None
        self.sa_email: Optional[str] = None
        self.region: Optional[str] = None
        self.credentials_dir: Optional[Path] = None
        self.credentials_filename: Optional[str] = None
        self.credentials_path: Optional[Path] = None
        self._credentials = None
        
    def get_credentials(self):
        """
        Get credentials with the correct quota project set
        
        Returns:
            Credentials object with quota_project_id set to self.project_id
        """
        if self._credentials is None:
            credentials, _ = google.auth.default()
            if self.project_id:
                # Set quota project to use the user-specified project
                self._credentials = credentials.with_quota_project(self.project_id)
            else:
                self._credentials = credentials
        return self._credentials
    
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")
    
    def check_authentication(self) -> bool:
        """
        Step 1: Pre-flight check - Verify user is authenticated with GCP
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        self.print_header("Step 1: Checking GCP Authentication")
        
        try:
            credentials, project = google.auth.default()
            self.print_success(f"Authenticated with GCP")
            if project:
                self.print_info(f"Default project: {project}")
            return True
        except DefaultCredentialsError:
            self.print_error("Not authenticated with GCP")
            print("\nPlease run: gcloud auth login")
            print("Then run: gcloud auth application-default login")
            return False
        except Exception as e:
            self.print_error(f"Authentication check failed: {e}")
            return False
    
    def validate_project_id(self, project_id: str) -> bool:
        """
        Validate GCP project ID format
        
        Args:
            project_id: The project ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # GCP project IDs must be 6-30 characters, lowercase letters, digits, hyphens
        pattern = r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$'
        return bool(re.match(pattern, project_id))
    
    def prompt_configuration(self):
        """
        Step 2: Interactive configuration - Prompt user for required variables
        """
        self.print_header("Step 2: Configuration")
        
        # Project ID (required, no default)
        while True:
            project_id = input("Enter GCP Project ID: ").strip()
            if not project_id:
                self.print_error("Project ID is required")
                continue
            if not self.validate_project_id(project_id):
                self.print_error("Invalid project ID format. Must be 6-30 chars, lowercase, letters/digits/hyphens")
                continue
            self.project_id = project_id
            break
        
        # Service Account Name
        default_sa_name = "car-buyer-assist-sa"
        sa_name = input(f"Enter Service Account Name [{default_sa_name}]: ").strip()
        self.sa_name = sa_name if sa_name else default_sa_name
        
        # Service Account Display Name
        default_display_name = "Car Buyer Assist SA"
        display_name = input(f"Enter Service Account Display Name [{default_display_name}]: ").strip()
        self.sa_display_name = display_name if display_name else default_display_name
        
        # Region
        default_region = "us-central1"
        region = input(f"Enter Region [{default_region}]: ").strip()
        self.region = region if region else default_region
        
        # Credentials Directory
        script_dir = Path(__file__).parent
        default_creds_dir = script_dir / "../../credentials"
        creds_dir = input(f"Enter Credentials Directory [{default_creds_dir}]: ").strip()
        self.credentials_dir = Path(creds_dir) if creds_dir else default_creds_dir
        
        # Credentials Filename
        default_filename = "gcp-service-account-key.json"
        filename = input(f"Enter Credentials Filename [{default_filename}]: ").strip()
        self.credentials_filename = filename if filename else default_filename
        
        # Derived values
        self.sa_email = f"{self.sa_name}@{self.project_id}.iam.gserviceaccount.com"
        self.credentials_path = self.credentials_dir / self.credentials_filename
        
        # Display configuration summary
        print("\n" + "-" * 70)
        print("Configuration Summary:")
        print(f"  Project ID: {self.project_id}")
        print(f"  Service Account Name: {self.sa_name}")
        print(f"  Service Account Email: {self.sa_email}")
        print(f"  Display Name: {self.sa_display_name}")
        print(f"  Region: {self.region}")
        print(f"  Credentials Path: {self.credentials_path.resolve()}")
        print("-" * 70)
        
        confirm = input("\nProceed with this configuration? (yes/no) [yes]: ").strip().lower()
        if confirm and confirm not in ['yes', 'y']:
            print("Setup cancelled by user")
            sys.exit(0)
        
        # Create credentials directory if it doesn't exist
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.print_success(f"Credentials directory ready: {self.credentials_dir.resolve()}")
    
    def enable_apis(self):
        """
        Step 3: Enable required GCP APIs
        """
        self.print_header("Step 3: Enabling Required APIs")
        
        apis_to_enable = [
            "aiplatform.googleapis.com",
            "cloudresourcemanager.googleapis.com",
            "iam.googleapis.com"
        ]
        
        try:
            # Use credentials with correct quota project
            credentials = self.get_credentials()
            client = service_usage_v1.ServiceUsageClient(credentials=credentials)
            parent = f"projects/{self.project_id}"
            
            for api in apis_to_enable:
                try:
                    service_name = f"{parent}/services/{api}"
                    
                    # Check if already enabled
                    try:
                        request = service_usage_v1.GetServiceRequest(name=service_name)
                        service = client.get_service(request=request)
                        if service.state == service_usage_v1.State.ENABLED:
                            self.print_info(f"API already enabled: {api}")
                            continue
                    except google_exceptions.NotFound:
                        pass
                    
                    # Enable the API
                    self.print_info(f"Enabling API: {api}")
                    request = service_usage_v1.EnableServiceRequest(name=service_name)
                    operation = client.enable_service(request=request)
                    operation.result(timeout=120)  # Wait for operation to complete
                    self.print_success(f"Enabled API: {api}")
                    
                except google_exceptions.PermissionDenied as e:
                    self.print_error(f"Permission denied for {api}: {e}")
                    self.print_info("Please ensure you have Owner or Editor role on the project")
                    raise
                except Exception as e:
                    self.print_warning(f"Could not enable {api}: {e}")
                    self.print_info(f"Continuing anyway (API may already be enabled)")
            
            self.print_success("All required APIs are ready")
            
        except Exception as e:
            self.print_error(f"Failed to enable APIs: {e}")
            raise
    
    def create_service_account(self):
        """
        Step 4: Create service account
        """
        self.print_header("Step 4: Creating Service Account")
        
        try:
            # Use credentials with correct quota project
            credentials = self.get_credentials()
            client = iam_admin_v1.IAMClient(credentials=credentials)
            parent = f"projects/{self.project_id}"
            
            # Check if service account already exists
            try:
                sa_resource_name = f"projects/{self.project_id}/serviceAccounts/{self.sa_email}"
                existing_sa = client.get_service_account(name=sa_resource_name)
                self.print_warning(f"Service account already exists: {self.sa_email}")
                self.print_info("Skipping creation and continuing with existing service account")
                return
            except google_exceptions.NotFound:
                # Service account doesn't exist, proceed with creation
                pass
            
            # Create the service account
            self.print_info(f"Creating service account: {self.sa_name}")
            
            service_account = iam_admin_v1.ServiceAccount(
                display_name=self.sa_display_name,
                description="Service account for Car Buyer Assist RAG Application - Vertex AI access"
            )
            
            request = iam_admin_v1.CreateServiceAccountRequest(
                name=parent,
                account_id=self.sa_name,
                service_account=service_account
            )
            
            created_sa = client.create_service_account(request=request)
            self.print_success(f"Created service account: {created_sa.email}")
            
        except google_exceptions.PermissionDenied as e:
            self.print_error(f"Permission denied: {e}")
            self.print_info("Please ensure you have Owner or Editor role on the project")
            raise
        except Exception as e:
            self.print_error(f"Failed to create service account: {e}")
            raise
    
    def grant_iam_roles(self):
        """
        Step 5: Grant IAM roles to service account
        """
        self.print_header("Step 5: Granting IAM Roles")
        
        roles_to_grant = [
            "roles/aiplatform.user",
            "roles/aiplatform.serviceAgent"
        ]
        
        try:
            # Use credentials with correct quota project
            credentials = self.get_credentials()
            client = resourcemanager_v3.ProjectsClient(credentials=credentials)
            project_name = f"projects/{self.project_id}"
            
            # Get current IAM policy
            self.print_info("Fetching current IAM policy...")
            policy = client.get_iam_policy(resource=project_name)
            
            # Add role bindings
            modified = False
            for role in roles_to_grant:
                member = f"serviceAccount:{self.sa_email}"
                
                # Check if binding already exists
                binding_exists = False
                for binding in policy.bindings:
                    if binding.role == role:
                        if member in binding.members:
                            self.print_info(f"Role already assigned: {role}")
                            binding_exists = True
                        else:
                            binding.members.append(member)
                            self.print_success(f"Added role: {role}")
                            modified = True
                        break
                
                # Create new binding if it doesn't exist
                if not binding_exists and not any(b.role == role for b in policy.bindings):
                    new_binding = {
                        "role": role,
                        "members": [member]
                    }
                    policy.bindings.append(new_binding)
                    self.print_success(f"Added role: {role}")
                    modified = True
            
            # Update IAM policy if modified
            if modified:
                self.print_info("Updating IAM policy...")
                client.set_iam_policy(resource=project_name, policy=policy)
                self.print_success("IAM roles granted successfully")
            else:
                self.print_info("All roles already assigned")
            
        except google_exceptions.PermissionDenied as e:
            self.print_error(f"Permission denied: {e}")
            self.print_info("Please ensure you have Owner or Editor role on the project")
            raise
        except Exception as e:
            self.print_error(f"Failed to grant IAM roles: {e}")
            raise
    
    def generate_credentials(self):
        """
        Step 6: Generate and save credentials file
        """
        self.print_header("Step 6: Generating Credentials")
        
        try:
            # Check if credentials file already exists
            if self.credentials_path.exists():
                self.print_warning(f"Credentials file already exists: {self.credentials_path}")
                self.print_info("Skipping credential generation")
                return
            
            # Generate service account key
            self.print_info(f"Generating service account key...")
            
            # Use credentials with correct quota project
            credentials = self.get_credentials()
            client = iam_admin_v1.IAMClient(credentials=credentials)
            sa_resource_name = f"projects/{self.project_id}/serviceAccounts/{self.sa_email}"
            
            request = iam_admin_v1.CreateServiceAccountKeyRequest(
                name=sa_resource_name,
                private_key_type=iam_admin_v1.ServiceAccountPrivateKeyType.TYPE_GOOGLE_CREDENTIALS_FILE
            )
            
            key = client.create_service_account_key(request=request)
            
            # Decode and save the key
            key_data = key.private_key_data
            
            with open(self.credentials_path, 'wb') as f:
                f.write(key_data)
            
            # Set appropriate permissions (owner read/write only)
            os.chmod(self.credentials_path, 0o600)
            
            self.print_success(f"Credentials saved: {self.credentials_path.resolve()}")
            self.print_info(f"File permissions set to 600 (owner read/write only)")
            
        except google_exceptions.PermissionDenied as e:
            self.print_error(f"Permission denied: {e}")
            raise
        except Exception as e:
            self.print_error(f"Failed to generate credentials: {e}")
            raise
    
    def validate_setup(self):
        """
        Step 7: Basic validation
        """
        self.print_header("Step 7: Validating Setup")
        
        try:
            # Validate service account exists
            # Use credentials with correct quota project
            credentials = self.get_credentials()
            client = iam_admin_v1.IAMClient(credentials=credentials)
            sa_resource_name = f"projects/{self.project_id}/serviceAccounts/{self.sa_email}"
            sa = client.get_service_account(name=sa_resource_name)
            self.print_success(f"Service account verified: {sa.email}")
            
            # Validate credentials file exists and is valid JSON
            if self.credentials_path.exists():
                with open(self.credentials_path, 'r') as f:
                    creds_data = json.load(f)
                    if 'type' in creds_data and creds_data['type'] == 'service_account':
                        self.print_success("Credentials file is valid")
                    else:
                        self.print_warning("Credentials file format may be incorrect")
            else:
                self.print_warning("Credentials file not found (may have been skipped)")
            
            self.print_success("Validation complete")
            
        except Exception as e:
            self.print_error(f"Validation failed: {e}")
            raise
    
    def print_summary(self):
        """
        Step 8: Display setup summary and next steps
        """
        self.print_header("Setup Complete!")
        
        print(f"{Colors.BOLD}Service Account Configuration:{Colors.ENDC}")
        print(f"  Email: {Colors.OKGREEN}{self.sa_email}{Colors.ENDC}")
        print(f"  Project: {self.project_id}")
        print(f"  Region: {self.region}")
        print()
        
        print(f"{Colors.BOLD}Assigned IAM Roles:{Colors.ENDC}")
        print(f"  • roles/aiplatform.user")
        print(f"  • roles/aiplatform.serviceAgent")
        print()
        
        print(f"{Colors.BOLD}Credentials:{Colors.ENDC}")
        print(f"  File: {Colors.OKGREEN}{self.credentials_path.resolve()}{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print(f"  1. Set environment variable:")
        print(f"     {Colors.OKCYAN}export GOOGLE_APPLICATION_CREDENTIALS=\"{self.credentials_path.resolve()}\"{Colors.ENDC}")
        print()
        print(f"  2. Or add to your .env file:")
        print(f"     {Colors.OKCYAN}GOOGLE_APPLICATION_CREDENTIALS={self.credentials_path.resolve()}{Colors.ENDC}")
        print()
        print(f"  3. Verify access:")
        print(f"     {Colors.OKCYAN}gcloud auth activate-service-account --key-file={self.credentials_path.resolve()}{Colors.ENDC}")
        print()
        
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ Setup completed successfully!{Colors.ENDC}\n")
    
    def run(self):
        """
        Main execution flow
        """
        try:
            # Step 1: Check authentication
            if not self.check_authentication():
                sys.exit(1)
            
            # Step 2: Prompt for configuration
            self.prompt_configuration()
            
            # Step 3: Enable APIs (skip if --skip-enable-apis)
            if self.skip_enable_apis:
                self.print_header("Step 3: Enabling Required APIs (Skipped)")
                self.print_info("Skipped - enable these APIs manually in GCP Console:")
                self.print_info("  • aiplatform.googleapis.com (Vertex AI)")
                self.print_info("  • cloudresourcemanager.googleapis.com")
                self.print_info("  • iam.googleapis.com")
                self.print_info("  Go to: https://console.cloud.google.com/apis/library")
            else:
                self.enable_apis()
            
            # Step 4: Create service account
            self.create_service_account()
            
            # Step 5: Grant IAM roles
            self.grant_iam_roles()
            
            # Step 6: Generate credentials
            self.generate_credentials()
            
            # Step 7: Validate setup
            self.validate_setup()
            
            # Step 8: Print summary
            self.print_summary()
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Setup interrupted by user{Colors.ENDC}")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n{Colors.FAIL}Setup failed: {e}{Colors.ENDC}")
            sys.exit(1)


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description="GCP Service Account Setup for Car Buyer Assist RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
If you get "Permission denied" when enabling APIs, use --skip-enable-apis:
  1. Create a new project at https://console.cloud.google.com (you'll be Owner)
  2. Enable APIs manually: APIs & Services > Library > enable:
     - Vertex AI API, Cloud Resource Manager API, IAM API
  3. Run: python setup_gcp_sa.py --skip-enable-apis
        """,
    )
    parser.add_argument(
        "--skip-enable-apis",
        action="store_true",
        help="Skip API enablement (use when you get permission errors; enable APIs manually in Console first)",
    )
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.HEADER}GCP Service Account Setup{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}Car Buyer Assist RAG Application{Colors.ENDC}\n")

    setup = GCPServiceAccountSetup(skip_enable_apis=args.skip_enable_apis)
    setup.run()


if __name__ == "__main__":
    main()

