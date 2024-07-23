### README for Rancher Error Notifier Script (Kubernetes Deployment)

#### Overview
This Rancher Error Notifier is a Kubernetes deployment designed to monitor Rancher Kubernetes environments specifically for errors and report these errors through Slack. It captures error logs within a specified time frame, processes them based on defined patterns, and posts the summaries to a designated Slack channel.

#### Files Included
1. `script.py`: Python script for capturing and processing error logs from Rancher.
2. `manifests.yml`: Kubernetes manifest for deploying the script as a CronJob.
3. `Dockerfile`: Defines a Docker container with the necessary environment for running the script.
4. `requirements.txt`: Lists the Python dependencies for the script.

#### Script Features
- **Kubernetes Integration**: Interacts with Kubernetes clusters to fetch logs from the Rancher application.
- **Slack Integration**: Sends processed error logs to a specified Slack channel.
- **Error Log Parsing**: Identifies errors in Rancher logs using regular expressions.
- **Time Filtering**: Only considers logs from the past `X_MINUTES`, which is configurable.
- **Local Timezone Adjustment**: Converts error log timestamps to a local timezone.
- **Debugging Support**: Optional debug mode for additional output and troubleshooting.

#### Kubernetes Deployment Configuration
The deployment and configuration of the script are managed through the `manifests.yml` file, which defines a Kubernetes CronJob and related resources.

- **CronJob**: Schedules the execution of the script at regular intervals.
- **ConfigMap**: Provides the Kubernetes cluster configuration.
- **Secret**: Securely stores the Slack token.

#### Environment Variables in `manifests.yml`
- `SLACK_TOKEN`: Slack API token for authorization.
- `CHANNEL_NAME`: Slack channel where notifications will be posted.
- `X_MINUTES`: Time frame for fetching recent logs.
- `LOCAL_TIME_OFFSET_HOURS`: Local timezone offset for timestamp conversion.
- `DEBUG`: Enables or disables debug mode.

#### Script Usage
- The script automatically fetches logs from pods labeled with `app=rancher` in the `cattle-system` namespace. It is specifically designed for Rancher logs and does not require modifications for different namespaces or app labels.
- It parses the logs for error patterns and sends a summary to the configured Slack channel.
- Use the environment variables in `manifests.yml` to customize the behavior of the script (e.g., adjusting the time frame for log retrieval).

#### Setup Instructions
1. **Configure `manifests.yml`**: Update the environment variables as needed.
2. **Build Docker Image**: Run `docker build -t rancher-error-notifier .` where the `Dockerfile` and `script.py` are located.
3. **Deploy to Kubernetes**: Apply `manifests.yml` in your Kubernetes cluster (`kubectl apply -f manifests.yml`).
4. **Monitor Slack Channel**: Check the specified Slack channel for error notifications.

#### Prerequisites
- Access to a Kubernetes cluster with Rancher installed.
- A Slack workspace with a channel for notifications.
- Permissions to deploy resources in Kubernetes.

#### Troubleshooting
- Verify that all environment variables in `manifests.yml` are correctly set.
- Check the logs of the Kubernetes CronJob for any execution errors.
- Ensure the Slack API token and channel are correctly configured and have the necessary permissions.

#### Future Enhancements
- Enhance error detection patterns for more comprehensive monitoring.
- Introduce notification thresholds or severity-based alerting.
- Develop a dashboard or reporting feature for tracking and analyzing error trends over time.
