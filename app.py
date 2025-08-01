import streamlit as st
import sqlite3
from datetime import datetime

DB = "database.db"  # Tên file SQLite trong cùng thư mục với app

# ---- Hàm tiện ích ----
def query_db(query, args=(), fetchone=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    data = cur.fetchone() if fetchone else cur.fetchall()
    conn.close()
    return data

st.set_page_config(page_title="POS TCH Demo", layout="centered")
st.title("💻 POS TCH - Demo CRM")

# --- Nhập số điện thoại ---
phone = st.text_input("📱 Nhập số điện thoại khách hàng:")

selected_voucher = None
ma_kh = None

if phone:
    # Kiểm tra khách cũ
    customer = query_db("SELECT MaKH, HoTen, HangHienTai FROM KhachHang WHERE SoDienThoai=?", (phone,), fetchone=True)
    
    if customer:
        st.success(f"Khách cũ: {customer[1] or 'Chưa có tên'} - Hạng: {customer[2] or 'Chưa xếp hạng'}")
        ma_kh = customer[0]
    else:
        st.warning("Khách mới! Hãy điền thông tin:")
        name = st.text_input("Họ tên khách mới:")
        dob = st.date_input("Ngày sinh (tùy chọn)")
        if st.button("Đăng ký khách mới"):
            query_db("INSERT INTO KhachHang (HoTen, NgaySinh, SoDienThoai, TongChiTieu) VALUES (?,?,?,0)", 
                     (name, dob, phone))
            st.success("✅ Đăng ký thành công! Tiếp tục tạo đơn cho khách mới.")
            ma_kh = query_db("SELECT MaKH FROM KhachHang WHERE SoDienThoai=?", (phone,), fetchone=True)[0]

# --- Nếu đã có khách hợp lệ (cũ hoặc mới vừa đăng ký) ---
if ma_kh:
    # --- Hiển thị voucher khả dụng ---
    st.subheader("🎁 Voucher khả dụng")
    vouchers = query_db("""
        SELECT VCN.MaVCN, VCN.Code, V.TenVoucher, VCN.TrangThai, V.LoaiVoucher, V.GiaTri
        FROM VoucherCaNhan VCN
        JOIN Voucher V ON VCN.MaVoucher = V.MaVoucher
        WHERE VCN.MaKH=? AND VCN.TrangThai='Available'
    """, (ma_kh,))
    
    if vouchers:
        options = {f"{v[1]} - {v[2]}": v for v in vouchers}
        selected_option = st.selectbox("Chọn voucher muốn áp dụng:", ["Không dùng"] + list(options.keys()))
        if selected_option != "Không dùng":
            selected_voucher = options[selected_option]
            st.info(f"Đã chọn voucher: {selected_voucher[1]} ({selected_voucher[2]})")
    else:
        st.write("❌ Không có voucher khả dụng.")

    # --- Chọn sản phẩm để tạo đơn ---
    st.subheader("🛒 Tạo đơn hàng")
    products = query_db("SELECT MaSP, TenSP, GiaMacDinh FROM SanPham")
    
    quantities = {}
    total = 0
    for p in products:
        qty = st.number_input(f"{p[1]} ({p[2]} VND)", min_value=0, max_value=10, step=1, key=f"sp_{p[0]}")
        if qty > 0:
            quantities[p[0]] = qty
            total += p[2] * qty
    
    # --- Áp dụng voucher nếu có ---
    discount_info = ""
    final_total = total
    if selected_voucher:
        if selected_voucher[4] == 'Discount':  # LoaiVoucher
            final_total = total * (100 - selected_voucher[5]) // 100
            discount_info = f"Áp dụng giảm {selected_voucher[5]}%"
        elif selected_voucher[4] == 'Gift':  # Tặng 1 ly
            final_total = max(total - 35000, 0)  # Giả sử giá 1 ly = 35k
            discount_info = "Áp dụng tặng 1 ly miễn phí"
    
    st.write(f"**Tổng tiền gốc: {total} VND**")
    if discount_info:
        st.write(f"**{discount_info} → Tổng thanh toán: {final_total} VND**")

    # --- Lưu đơn hàng ---
    if st.button("💾 Lưu đơn hàng"):
        if total == 0:
            st.error("Chưa chọn sản phẩm!")
        else:
            # Lưu đơn hàng
            query_db("INSERT INTO DonHang (MaKH, MaCH, TongTien, ThoiGianDat) VALUES (?,?,?,?)",
                     (ma_kh, 1, final_total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            ma_don = query_db("SELECT last_insert_rowid()", fetchone=True)[0]

            # Lưu chi tiết
            for ma_sp, qty in quantities.items():
                query_db("INSERT INTO ChiTietDonHang (MaDon, MaSP, SoLuong) VALUES (?,?,?)", (ma_don, ma_sp, qty))

            # Đánh dấu voucher đã dùng
            if selected_voucher:
                query_db("UPDATE VoucherCaNhan SET TrangThai='Used' WHERE MaVCN=?", (selected_voucher[0],))

            st.success(f"✅ Đã lưu đơn hàng #{ma_don} thành công! Tổng thanh toán: {final_total} VND")
