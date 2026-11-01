# SPDX-License-Identifier: MPL-2.0
# A Configuration Studio component that is one self-contained jar, the service or the store writer, for the test harness
# (tools/testing/studio_harness). The build context holds the jar as app.jar. The component reads its configuration from the environment.
FROM eclipse-temurin:25-jre-alpine
RUN adduser -D -H studio && mkdir /opt/studio && chmod 755 /opt/studio
COPY --chmod=644 app.jar /opt/studio/app.jar
USER studio
ENTRYPOINT ["java", "-jar", "/opt/studio/app.jar"]
