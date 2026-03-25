FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /run/sshd

# Create the SAP admin user
RUN useradd -m -s /bin/bash devadm

# SSH config: key-only auth, no password
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Set up authorized key for devadm
RUN mkdir -p /home/devadm/.ssh && chmod 700 /home/devadm/.ssh
COPY ssh/id_ed25519.pub /home/devadm/.ssh/authorized_keys
RUN chmod 600 /home/devadm/.ssh/authorized_keys && \
    chown -R devadm:devadm /home/devadm/.ssh

# Install mock sapcontrol and df
COPY scripts/sapcontrol /usr/local/bin/sapcontrol
COPY scripts/mock_df /usr/local/bin/df
RUN chmod +x /usr/local/bin/sapcontrol /usr/local/bin/df

# Setup script (populates trace files at container start)
COPY scripts/setup_files.sh /usr/local/bin/setup_files.sh
RUN chmod +x /usr/local/bin/setup_files.sh

# Create base SAP directory structure
RUN mkdir -p /usr/sap/DEV/work /usr/sap/DEV/data && \
    chown -R devadm:devadm /usr/sap

EXPOSE 22

# Entrypoint: populate files for scenario, write env for SSH sessions, start sshd
CMD /bin/bash -c '\
    export SAP_SCENARIO=${SAP_SCENARIO:-1} && \
    echo "SAP_SCENARIO=$SAP_SCENARIO" >> /home/devadm/.bashrc && \
    echo "export SAP_SCENARIO=$SAP_SCENARIO" >> /home/devadm/.bashrc && \
    echo "AcceptEnv SAP_SCENARIO" >> /etc/ssh/sshd_config && \
    echo "PermitUserEnvironment yes" >> /etc/ssh/sshd_config && \
    echo "SAP_SCENARIO=$SAP_SCENARIO" > /home/devadm/.ssh/environment && \
    chown devadm:devadm /home/devadm/.ssh/environment && \
    /usr/local/bin/setup_files.sh && \
    echo "[sap-mock] Ready — scenario $SAP_SCENARIO, SSH on port 22" && \
    exec /usr/sbin/sshd -D'
