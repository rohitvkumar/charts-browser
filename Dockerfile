FROM nginx:alpine

RUN apk add --no-cache python3 py3-pip && \
    pip install --break-system-packages markdown || pip install markdown

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /app/entrypoint.sh
COPY render_md.py /app/render_md.py
COPY generate_chart_index.py /app/generate_chart_index.py
COPY regenerate_server.py /app/regenerate_server.py
COPY styles.css /usr/share/nginx/html/styles.css
COPY stop_loss.html /usr/share/nginx/html/stop-loss/index.html
COPY daily_stop_loss.html /usr/share/nginx/html/daily-stop-loss/index.html
COPY buy_point.html /usr/share/nginx/html/buy-point/index.html
RUN chmod +x /app/entrypoint.sh /app/render_md.py /app/generate_chart_index.py /app/regenerate_server.py

RUN mkdir -p /md_src /usr/share/nginx/html/md /usr/share/nginx/html/stop-loss /usr/share/nginx/html/daily-stop-loss /usr/share/nginx/html/buy-point

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]