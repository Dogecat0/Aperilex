#!/bin/bash
# pulumi down --exclude "**aperilex-frontend-cdn" --exclude "**aperilex-backend-prod-env" --exclude "**aperilex-db-cluster" --exclude "**internet-gateway"
pulumi down --exclude-protected --exclude "**aperilex-frontend-cdn" --exclude "**aperilex-backend-prod-env" --exclude "**aperilex-db-cluster" --exclude "**internet-gateway"
