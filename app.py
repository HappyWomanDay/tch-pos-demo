import streamlit as st
import sqlite3
from datetime import datetime

DB = "database.db"  # Tên file SQLite

# Hàm chạy query
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

if phone:
    # Kiểm tra khách cũ hay mới
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
    
            # Lấy MaKH vừa tạo
            ma_kh = query_db("SELECT MaKH FROM KhachHang WHERE SoDienThoai=?", (phone,), fetchone=True)[0]
        else:
            ma_kh = None

    # --- Hiển thị voucher khả dụng ---
    if ma_kh:
        st.subheader("🎁 Voucher khả dụng")
        vouchers = query_db("""
            SELECT VCN.Code, V.TenVoucher, VCN.TrangThai
            FROM VoucherCaNhan VCN
            JOIN Voucher V ON VCN.MaVoucher = V.MaVoucher
            WHERE VCN.MaKH=? AND VCN.TrangThai='Available'
        """, (ma_kh,))
        
        if vouchers:
            for v in vouchers:
                st.write(f"- **{v[0]}**: {v[1]} ({v[2]})")
        else:
            st.write("❌ Không có voucher khả dụng.")
        
        # --- Chọn sản phẩm tạo đơn ---
        st.subheader("🛒 Tạo đơn hàng")
        products = query_db("SELECT MaSP, TenSP, GiaMacDinh FROM SanPham")
        
        quantities = {}
        total = 0
        for p in products:
            qty = st.number_input(f"{p[1]} ({p[2]} VND)", min_value=0, max_value=10, step=1)
            if qty > 0:
                quantities[p[0]] = qty
                total += p[2] * qty
        
        st.write(f"**Tổng tiền: {total} VND**")
        
        if st.button("💾 Lưu đơn hàng"):
            if total == 0:
                st.error("Chưa chọn sản phẩm!")
            else:
                query_db("INSERT INTO DonHang (MaKH, MaCH, TongTien, ThoiGianDat) VALUES (?,?,?,?)",
                         (ma_kh, 1, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                ma_don = query_db("SELECT last_insert_rowid()", fetchone=True)[0]
                
                for ma_sp, qty in quantities.items():
                    query_db("INSERT INTO ChiTietDonHang (MaDon, MaSP, SoLuong) VALUES (?,?,?)", (ma_don, ma_sp, qty))
                
                st.success(f"✅ Đã lưu đơn hàng #{ma_don} thành công!")
