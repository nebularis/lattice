# SPDX-License-Identifier: MPL-2.0
# Fuseki for the Configuration Studio, from the Apache Jena release on Maven Central, pinned by
# checksum. An in-memory dataset "studio" with updates enabled.
FROM eclipse-temurin:25-jre-alpine
ADD --checksum=sha256:2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee \
    https://repo1.maven.org/maven2/org/apache/jena/jena-fuseki-server/6.2.0/jena-fuseki-server-6.2.0.jar /opt/fuseki/fuseki-server.jar
RUN adduser -D -H fuseki
USER fuseki
EXPOSE 3030
ENTRYPOINT ["java", "-jar", "/opt/fuseki/fuseki-server.jar", "--port", "3030", "--mem", "--update", "/studio"]
