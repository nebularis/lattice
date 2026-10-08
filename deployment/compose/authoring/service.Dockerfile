FROM eclipse-temurin:25-jre
COPY authoring-service.jar /app/authoring-service.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/authoring-service.jar"]
